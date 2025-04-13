import json
import os
import asyncio
import websockets
from datetime import datetime
from newspaper import Article
from openai import OpenAI
import psycopg2
from psycopg2.extras import execute_batch
from typing import List, Dict
import logging
from TrendAnalysis import analyze_and_display 

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment setup
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Database connection
conn = psycopg2.connect(
    "dbname=banan user=timeframe_webserver password=1234 host=localhost"
)

def get_source_type(source: str) -> str:
    source_lower = source.lower()
    if 'twitter' in source_lower: return 'TWITTER'
    if 'reddit' in source_lower: return 'REDDIT'
    if 'youtube' in source_lower: return 'YOUTUBE'
    if 'spotify' in source_lower: return 'SPOTIFY'
    return 'GENERIC'

async def fetch_scraper_data() -> List[Dict]:
    uri = "ws://localhost:8765"
    async with websockets.connect(uri) as websocket:
        request = {
            'action': 'get_snapshot',
            'timestamp': datetime.now().isoformat(),
            'youtube': True,
            'reddit': True,
            'spotify': True,
            'twitter': True
        }
        await websocket.send(json.dumps(request))
        response = await websocket.recv()
        data = json.loads(response)
        if data['status'] == 'success':
            return data['data']
        raise Exception(data.get('message', 'Failed to fetch snapshot'))

def transform_scraper_format(scraper_data: List[Dict]) -> List[Dict]:
    transformed = []
    for article in scraper_data:
        try:
            dt = datetime.fromisoformat(article['timestamp'])
            transformed.append({
                'title': article['title'],
                'date': dt.strftime('%Y-%m-%d'),
                'source': article['source'],
                'url': article['link'],
                '_original': {
                    'description': article['description'],
                    'content': article['content'],
                    'timestamp': article['timestamp']
                }
            })
        except KeyError as e:
            logger.warning(f"Skipping invalid article: Missing {str(e)}")
    return transformed

class ContentProcessor:
    def __init__(self, user_email: str = "wdbros@gmail.com"):
        self.user_email = user_email
        self.client = OpenAI(api_key="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")  # ✅ Secure key loading
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

    def generate_summary(self, text: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{
                    "role": "system",
                    "content": "Create a concise headline and one-sentence summary."
                }, {
                    "role": "user",
                    "content": f"Articles:\n{text[:12000]}\n\nSummary:"
                }],
                temperature=0.3,
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API Error: {str(e)}")
            return "Summary unavailable"

    def process_clusters(self, result: Dict, scraper_data: List[Dict]) -> None:
        with conn:
            with conn.cursor() as cur:
                try:
                    cur.execute("""
                        INSERT INTO "user" (id, last_login)
                        VALUES (%s, %s)
                        ON CONFLICT (id) DO UPDATE
                        SET last_login = EXCLUDED.last_login
                    """, (self.user_email, datetime.now()))

                    article_map = {a['link']: a for a in scraper_data}  # ✅ Optimization

                    for cluster in result.get('high_trend_clusters', []):
                        cluster_urls = cluster['articles']
                        cluster_articles = [
                            article_map[url] for url in cluster_urls if url in article_map
                        ]
                        timestamps = [
                            datetime.fromisoformat(a['timestamp'])
                            for a in cluster_articles
                        ]

                        if not timestamps:
                            logger.warning(f"No valid timestamps for cluster: {cluster_urls}")
                            continue

                        earliest_ts = min(timestamps)
                        contents = [self.get_article_text(url) for url in cluster_urls]
                        combined_text = "\n\n".join(filter(None, contents))
                        summary = self.generate_summary(combined_text)

                        headline = summary.split('.')[0][:255] if summary else "No headline"
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
                                feed_data.append((
                                    datetime.fromisoformat(article['timestamp']),
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
                        for a in scraper_data
                    }
                    if sources:
                        execute_batch(cur, """
                            INSERT INTO source (source, type, "user")
                            VALUES (%s, %s, %s)
                            ON CONFLICT (source, "user") DO NOTHING
                        """, [(s[0], s[1], self.user_email) for s in sources])

                except Exception as e:
                    conn.rollback()
                    logger.error(f"Database error: {str(e)}")
                    raise

async def main():
    try:
        scraper_data = await fetch_scraper_data()
        articles = transform_scraper_format(scraper_data)
        
        if not articles:
            logger.info("No articles received from scraper")
            return

        logger.info("Running trend detection...")
        result = analyze_and_display(articles)
        
        processor = ContentProcessor()
        processor.process_clusters(result, scraper_data)
        
        logger.info("✅ Successfully processed all data")

    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    asyncio.run(main())