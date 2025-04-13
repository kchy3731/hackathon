#!/usr/bin/env python3
import psycopg2
from datetime import datetime

# Connect directly to the database
conn = psycopg2.connect(
    dbname="banan",
    user="timeframe_webserver",
    password="1234",
    host="localhost"
)

try:
    cursor = conn.cursor()
    
    # Insert a test article
    print("Inserting test article...")
    
    # First, check if the article already exists
    check_query = """
    SELECT id FROM regular_feed 
    WHERE headline = 'Test Article' AND "user" = 'timeframe_webserver'
    """
    cursor.execute(check_query)
    
    if cursor.fetchone() is None:
        # Insert the article
        insert_query = """
        INSERT INTO regular_feed (timestamp, headline, link, "user")
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """
        
        cursor.execute(insert_query, (
            datetime.now(),
            "Test Article",
            "https://example.com/test",
            "timeframe_webserver"
        ))
        
        article_id = cursor.fetchone()[0]
        conn.commit()
        print(f"Test article inserted with ID: {article_id}")
    else:
        print("Test article already exists")
    
    # Verify the article was inserted
    print("\nVerifying article insertion:")
    cursor.execute("SELECT * FROM regular_feed WHERE headline = 'Test Article'")
    results = cursor.fetchall()
    print(f"Found {len(results)} articles:")
    for row in results:
        print(row)
    
finally:
    cursor.close()
    conn.close()
