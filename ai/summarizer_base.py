import os
import time
from datetime import datetime, timedelta
from newspaper import Article
from groq import Groq  # Using Groq for headline generation
import psycopg2
from psycopg2.extras import execute_batch, RealDictCursor
from typing import List, Dict
import logging
from dotenv import load_dotenv
from TrendAnalysis import analyze_and_display

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment setup
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Database connection function
def get_db_connection():
    return psycopg2.connect(
        "dbname=banan user=timeframe_webserver password=1234 host=localhost"
    )

# Initial database connection
conn = get_db_connection()

def get_source_type(source: str) -> str:
    source_lower = source.lower()
    if 'twitter' in source_lower: return 'TWITTER'
    if 'reddit' in source_lower: return 'REDDIT'
    if 'youtube' in source_lower: return 'YOUTUBE'
    if 'spotify' in source_lower: return 'SPOTIFY'
    return 'GENERIC'

def fetch_articles_from_db(days_ago: int = 7, user_id: str = 'wdbros@gmail.com') -> List[Dict]:
    """Fetch recent articles from the PostgreSQL database

    Args:
        days_ago: Number of days to look back for articles
        user_id: User ID to fetch articles for

    Returns:
        List of article dictionaries
    """
    logger.info(f"Fetching articles from database for the last {days_ago} days")

    # Calculate the date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days_ago)

    articles = []

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Query to get recent articles
            query = """
            SELECT rf.id, rf.timestamp, rf.headline as title, rf.link, s.source, s.type
            FROM regular_feed rf
            LEFT JOIN source s ON s.user = rf.user
            WHERE rf.user = %s AND rf.timestamp >= %s
            ORDER BY rf.timestamp DESC
            """

            cur.execute(query, (user_id, start_date))
            articles = cur.fetchall()

            logger.info(f"Found {len(articles)} articles in the database")

    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        conn.rollback()

    return articles

def transform_db_format(db_articles: List[Dict]) -> List[Dict]:
    """Transform database articles to the format expected by TrendAnalysis

    Args:
        db_articles: List of articles from the database

    Returns:
        List of transformed articles
    """
    transformed = []

    # Print the first article for debugging
    if db_articles:
        logger.info(f"First article from DB: {db_articles[0]}")
        logger.info(f"Timestamp type: {type(db_articles[0]['timestamp'])}")

    for article in db_articles:
        try:
            # Handle timestamp - could be string or datetime object
            if isinstance(article['timestamp'], str):
                dt = datetime.fromisoformat(article['timestamp'])
            else:
                dt = article['timestamp']

            # Format the date string properly - TrendAnalysis expects a string in this format
            date_str = dt.strftime('%Y-%m-%d')

            # Debug log
            logger.debug(f"Converted date: {date_str}, type: {type(date_str)}")

            transformed.append({
                'title': article['title'] if article['title'] else 'No Title',
                'date': date_str,  # Always provide a string in the expected format
                'source': article['source'] if article['source'] else 'Unknown',
                'url': article['link'],
                '_original': {
                    'id': article['id'],
                    'timestamp': dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)
                }
            })
        except KeyError as e:
            logger.warning(f"Skipping invalid article: Missing {str(e)}")
    return transformed

class ContentProcessor:
    def __init__(self, user_email: str = "wdbros@gmail.com"):
        self.user_email = user_email
        # Get Groq API key from environment variables (loaded via dotenv)
        groq_api_key = os.environ.get("GROQ_API_KEY")
        if not groq_api_key:
            logger.warning("GROQ_API_KEY not found in environment variables. Summaries will not be generated.")
        self.groq_client = Groq(api_key=groq_api_key)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }

    def get_article_text(self, url: str) -> str:
        try:
            article = Article(url, browser_user_agent=self.headers['User-Agent'], request_timeout=10)
            article.download()
            article.parse()
            return article.text.strip() if len(article.text.strip()) > 100 else ""
        except Exception as e:
            logger.warning(f"⚠️ Failed to process article: {url}\nError: {str(e)[:200]}...")
            return ""

    def generate_headline_and_summary(self, text: str) -> tuple:
        """Generate a headline and summary for the given text

        Args:
            text: The text to summarize

        Returns:
            tuple: (headline, summary)
        """
        # Check if Groq client is properly initialized with an API key
        if not self.groq_client.api_key:
            logger.warning("Skipping summary generation: No Groq API key available")
            return "No headline available", "Summary unavailable - No API key"

        try:
            # Using Groq with LLaMA 3 model for headline and summary generation
            response = self.groq_client.chat.completions.create(
                model="llama3-8b-8192",  # Using LLaMA 3 model
                messages=[{
                    "role": "system",
                    "content": "Generate two separate parts: 1) A concise headline (maximum 10 words) and 2) A one-sentence summary. Format your response exactly as 'Headline: [your headline]\nSummary: [your summary]'\n\nIMPORTANT RULES:\n- Focus ONLY on the actual article content, not on website features, login pages, or community aspects.\n- DO NOT create headlines about 'joining communities', 'creating accounts', 'signing up', or similar website functionality.\n- If the content appears to be primarily about a website interface rather than actual news/content, respond with 'Headline: [Unable to extract meaningful content]\nSummary: [Content appears to be about website interface rather than article content]'\n- Ensure the headline and summary reflect the substantive content of the article, not the platform it's on."
                }, {
                    "role": "user",
                    "content": f"Articles:\n{text[:12000]}\n\nPlease provide a headline and summary:"
                }],
                temperature=0.3,
                max_tokens=200
            )

            content = response.choices[0].message.content.strip()

            # Parse the response to extract headline and summary
            headline = "No headline available"
            summary = "No summary available"

            # Try to extract headline and summary using the expected format
            headline_match = content.split("\n")[0] if "\n" in content else content
            if headline_match.lower().startswith("headline:"):
                headline = headline_match[len("headline:"):].strip()
            else:
                # Fallback: use the first sentence as headline
                headline = content.split(".")[0].strip()

            # Try to extract summary
            if "\n" in content and len(content.split("\n")) > 1:
                summary_line = content.split("\n")[1]
                if summary_line.lower().startswith("summary:"):
                    summary = summary_line[len("summary:"):].strip()
                else:
                    # If we can't find a properly formatted summary, use the rest of the content
                    summary = "\n".join(content.split("\n")[1:]).strip()
            else:
                # Fallback: use everything after the first sentence as summary
                parts = content.split(".", 1)
                if len(parts) > 1:
                    summary = parts[1].strip()

            # Filter out summaries about login pages or website descriptions
            login_keywords = ["join", "sign up", "create account", "log in", "login", "register", "community guidelines",
                             "password", "username", "email address", "subscribe", "membership"]

            # Check if the headline is about login/signup
            is_login_headline = False
            headline_lower = headline.lower()
            for keyword in login_keywords:
                if keyword in headline_lower:
                    is_login_headline = True
                    break

            # Check if the summary is about login/signup
            is_login_summary = False
            summary_lower = summary.lower()
            for keyword in login_keywords:
                if keyword in summary_lower:
                    is_login_summary = True
                    break

            # If either headline or summary is about login/signup, replace both
            if is_login_headline or is_login_summary or headline == "[Unable to extract meaningful content]":
                logger.warning("Detected login/signup content in summary, replacing with generic message")
                return "Article content unavailable", "The article content could not be extracted properly."

            return headline[:255], summary[:1000]  # Limit lengths to database field sizes
        except Exception as e:
            logger.error(f"Groq API Error: {str(e)}")
            return "API Error - No headline", "Summary unavailable - API error"

    def process_clusters(self, result: Dict, db_articles: List[Dict]) -> None:
        with conn:
            with conn.cursor() as cur:
                try:
                    cur.execute("""
                        INSERT INTO "user" (id, last_login)
                        VALUES (%s, %s)
                        ON CONFLICT (id) DO UPDATE
                        SET last_login = EXCLUDED.last_login
                    """, (self.user_email, datetime.now()))

                    article_map = {a['link']: a for a in db_articles}  # ✅ Optimization

                    for cluster in result.get('high_trend_clusters', []):
                        cluster_urls = cluster['articles']
                        cluster_articles = [
                            article_map[url] for url in cluster_urls if url in article_map
                        ]
                        timestamps = []
                        for a in cluster_articles:
                            if isinstance(a['timestamp'], str):
                                timestamps.append(datetime.fromisoformat(a['timestamp']))
                            else:
                                timestamps.append(a['timestamp'])

                        if not timestamps:
                            logger.warning(f"No valid timestamps for cluster: {cluster_urls}")
                            continue

                        earliest_ts = min(timestamps)
                        contents = [self.get_article_text(url) for url in cluster_urls]
                        combined_text = "\n\n".join(filter(None, contents))
                        headline, summary = self.generate_headline_and_summary(combined_text)
                        cur.execute("""
                            INSERT INTO highlight (timestamp, headline, body, "user")
                            VALUES (%s, %s, %s, %s)
                            RETURNING id
                        """, (earliest_ts, headline, summary[:1000], self.user_email))
                        highlight_id = cur.fetchone()[0]

                        feed_data = []
                        for url in cluster_urls:
                            article = article_map.get(url)
                            if article:
                                # Handle both string and datetime objects for timestamp
                                timestamp = article['timestamp']
                                if isinstance(timestamp, str):
                                    timestamp = datetime.fromisoformat(timestamp)
                                # Otherwise, assume it's already a datetime object

                                feed_data.append((
                                    timestamp,
                                    (article['title'] or '')[:255],  # ✅ Safe fallback
                                    url,
                                    highlight_id,
                                    self.user_email
                                ))

                        if feed_data:
                            execute_batch(cur, """
                                INSERT INTO regular_feed (timestamp, headline, link, highlight, "user")
                                VALUES (%s, %s, %s, %s, %s)
                            """, feed_data)

                    sources = {
                        (a['source'], get_source_type(a['source']))
                        for a in db_articles if 'source' in a and a['source']
                    }
                    if sources:
                        # First check if the source already exists before inserting
                        for s in sources:
                            try:
                                # Check if the source already exists
                                cur.execute("""
                                    SELECT 1 FROM source
                                    WHERE source = %s AND "user" = %s
                                """, (s[0], self.user_email))

                                # If the source doesn't exist, insert it
                                if cur.fetchone() is None:
                                    cur.execute("""
                                        INSERT INTO source (source, type, "user")
                                        VALUES (%s, %s, %s)
                                    """, (s[0], s[1], self.user_email))
                            except Exception as source_error:
                                logger.warning(f"Error handling source {s[0]}: {str(source_error)}")

                except Exception as e:
                    conn.rollback()
                    logger.error(f"Database error: {str(e)}")
                    raise

def get_latest_article_timestamp():
    """Get the timestamp of the most recent article in the database"""
    connection = get_db_connection()
    try:
        with connection.cursor() as cur:
            cur.execute("""
                SELECT MAX(timestamp) FROM regular_feed
            """)
            result = cur.fetchone()[0]
            return result if result else datetime.min
    except Exception as e:
        logger.error(f"Error getting latest article timestamp: {str(e)}")
        return datetime.min
    finally:
        connection.close()

def main(continuous_mode=False):
    """Main function to process articles

    Args:
        continuous_mode: If True, the function will return a boolean indicating if new articles were processed
    """
    # Create a new connection for this run
    connection = get_db_connection()

    # Temporarily set the global conn to this connection
    global conn
    old_conn = conn
    conn = connection

    try:
        # Fetch articles from the database instead of the scraper
        db_articles = fetch_articles_from_db(days_ago=7)
        articles = transform_db_format(db_articles)

        if not articles:
            logger.info("No articles found in the database")
            return False if continuous_mode else None

        # Debug log the first transformed article
        if articles:
            logger.info(f"First transformed article: {articles[0]}")
            logger.info(f"Date type: {type(articles[0]['date'])}")

        logger.info("Running trend detection...")
        result = analyze_and_display(articles)

        processor = ContentProcessor()
        processor.process_clusters(result, db_articles)

        logger.info("✅ Successfully processed all data")
        return True if continuous_mode else None

    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
        return False if continuous_mode else None
    finally:
        # Close the connection we created
        connection.close()

        # Restore the original connection if in continuous mode
        if continuous_mode:
            conn = old_conn

def continuous_run(check_interval=300):  # 5 minutes by default
    """Run the main function continuously, but only when there are new articles

    Args:
        check_interval: Time in seconds between checks for new articles
    """
    logger.info(f"Starting continuous mode with check interval of {check_interval} seconds")

    # Run the main function once at startup
    main()

    last_processed_timestamp = get_latest_article_timestamp()
    logger.info(f"Initial latest article timestamp: {last_processed_timestamp}")

    try:
        while True:
            # Sleep for the specified interval
            time.sleep(check_interval)

            # Check if there are new articles
            current_latest = get_latest_article_timestamp()

            if current_latest > last_processed_timestamp:
                logger.info(f"New articles detected! Last processed: {last_processed_timestamp}, Current latest: {current_latest}")
                # Run the main function again
                processed = main(continuous_mode=True)

                if processed:
                    last_processed_timestamp = current_latest
            else:
                logger.info(f"No new articles detected. Last processed: {last_processed_timestamp}")
    except KeyboardInterrupt:
        logger.info("Continuous mode stopped by user")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Process articles from the database')
    parser.add_argument('--continuous', action='store_true', help='Run in continuous mode')
    parser.add_argument('--interval', type=int, default=300, help='Check interval in seconds (default: 300)')

    args = parser.parse_args()

    if args.continuous:
        continuous_run(check_interval=args.interval)
    else:
        main()