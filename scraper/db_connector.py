import psycopg2
from psycopg2 import pool
from datetime import datetime
from scraper import article

# Database connection parameters
DB_PARAMS = {
    "dbname": "banan",
    "user": "timeframe_webserver",
    "password": "1234",
    "host": "localhost"
}

# Create a connection pool
connection_pool = None

def init_connection_pool(min_conn=1, max_conn=10):
    """Initialize the database connection pool"""
    global connection_pool
    try:
        connection_pool = pool.ThreadedConnectionPool(
            min_conn,
            max_conn,
            **DB_PARAMS
        )
        print("Connection pool created successfully")
    except Exception as e:
        print(f"Error creating connection pool: {e}")
        raise e

def get_connection():
    """Get a connection from the pool"""
    if connection_pool is None:
        init_connection_pool()
    return connection_pool.getconn()

def release_connection(conn):
    """Release a connection back to the pool"""
    if connection_pool is not None:
        connection_pool.putconn(conn)

def get_rss_sources(user_id='wdbros@gmail.com'):
    """Get all RSS sources for a user from the database"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # First, let's get ALL sources to debug
        debug_query = "SELECT id, type, source FROM source WHERE \"user\" = %s"
        print(f"Executing debug query: {debug_query} with user_id: {user_id}")
        cursor.execute(debug_query, (user_id,))
        all_sources = cursor.fetchall()
        print(f"All sources: {all_sources}")

        # Now get just RSS sources
        query = "SELECT source FROM source WHERE type = 'RSS' AND \"user\" = %s"
        print(f"Executing query: {query} with user_id: {user_id}")
        cursor.execute(query, (user_id,))

        # Fetch all results
        results = cursor.fetchall()
        print(f"Query returned {len(results)} results: {results}")
        sources = [row[0] for row in results]

        # If no results, try a more flexible approach
        if not sources:
            print("No results with exact match, trying with LIKE")
            query = "SELECT source FROM source WHERE type LIKE '%RSS%'"
            cursor.execute(query)
            results = cursor.fetchall()
            print(f"LIKE query returned {len(results)} results: {results}")
            sources = [row[0] for row in results]

        cursor.close()
        return sources
    except Exception as e:
        print(f"Error fetching RSS sources: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        if conn:
            release_connection(conn)

def save_article_to_db(article_obj, user_id='wdbros@gmail.com'):
    """Save an article to the regular_feed table"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if article already exists to avoid duplicates
        # First check by exact link match (most reliable)
        check_query = """
        SELECT id FROM regular_feed
        WHERE link = %s AND "user" = %s
        """
        cursor.execute(check_query, (
            article_obj.link,
            user_id
        ))

        result = cursor.fetchone()
        if result is not None:
            article_id = result[0]
            print(f"Skipping duplicate article (by link): {article_obj.title} | {article_obj.link} | ID: {article_id}")
            cursor.close()
            return None

        # If no match by link, also check by headline for additional safety
        check_query = """
        SELECT id FROM regular_feed
        WHERE headline = %s AND "user" = %s
        """
        cursor.execute(check_query, (
            article_obj.title,
            user_id
        ))

        result = cursor.fetchone()
        if result is not None:
            article_id = result[0]
            print(f"Skipping duplicate article (by headline): {article_obj.title} | {article_obj.link} | ID: {article_id}")
            cursor.close()
            return None

        # Insert the article if it doesn't exist
        insert_query = """
        INSERT INTO regular_feed (timestamp, headline, link, "user")
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """

        cursor.execute(insert_query, (
            article_obj.timestamp,
            article_obj.title,
            article_obj.link,
            user_id
        ))

        article_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Saved new article: {article_obj.title} | {article_obj.link} | ID: {article_id}")
        cursor.close()
        return article_id
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Error saving article to database: {e}")
        return None
    finally:
        if conn:
            release_connection(conn)

def save_articles_to_db(articles, user_id='wdbros@gmail.com'):
    """Save multiple articles to the database"""
    saved_count = 0
    for article_obj in articles:
        if save_article_to_db(article_obj, user_id):
            saved_count += 1

    return saved_count

def get_recent_articles(limit=50, user_id='wdbros@gmail.com'):
    """Get recent articles from the database"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()

        query = """
        SELECT id, timestamp, headline, link
        FROM regular_feed
        WHERE "user" = %s
        ORDER BY timestamp DESC
        LIMIT %s
        """

        cursor.execute(query, (user_id, limit))

        articles = []
        for row in cursor.fetchall():
            articles.append({
                'id': row[0],
                'timestamp': row[1].isoformat() if isinstance(row[1], datetime) else row[1],
                'headline': row[2],
                'link': row[3]
            })

        cursor.close()
        return articles
    except Exception as e:
        print(f"Error fetching recent articles: {e}")
        return []
    finally:
        if conn:
            release_connection(conn)

def close_connection_pool():
    """Close the connection pool"""
    if connection_pool is not None:
        connection_pool.closeall()
        print("Connection pool closed")

if __name__ == "__main__":
    # Test the connection
    init_connection_pool()
    sources = get_rss_sources()
    print(f"Found {len(sources)} RSS sources")
    for source in sources:
        print(f"  - {source}")
    close_connection_pool()
