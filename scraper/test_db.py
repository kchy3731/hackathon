#!/usr/bin/env python3
import psycopg2

# Connect directly to the database
conn = psycopg2.connect(
    dbname="banan",
    user="timeframe_webserver",
    password="1234",
    host="localhost"
)

try:
    cursor = conn.cursor()
    
    # Get all sources
    print("Fetching all sources:")
    cursor.execute("SELECT * FROM source")
    results = cursor.fetchall()
    print(f"Found {len(results)} sources:")
    for row in results:
        print(row)
    
    # Get RSS sources
    print("\nFetching RSS sources:")
    cursor.execute("SELECT * FROM source WHERE type = 'RSS'")
    results = cursor.fetchall()
    print(f"Found {len(results)} RSS sources:")
    for row in results:
        print(row)
    
    # Get sources for specific user
    user_id = 'wdbros@gmail.com'
    print(f"\nFetching sources for user {user_id}:")
    cursor.execute("SELECT * FROM source WHERE user = %s", (user_id,))
    results = cursor.fetchall()
    print(f"Found {len(results)} sources for user {user_id}:")
    for row in results:
        print(row)
    
    # Get RSS sources for specific user
    print(f"\nFetching RSS sources for user {user_id}:")
    cursor.execute("SELECT * FROM source WHERE type = 'RSS' AND user = %s", (user_id,))
    results = cursor.fetchall()
    print(f"Found {len(results)} RSS sources for user {user_id}:")
    for row in results:
        print(row)
    
finally:
    cursor.close()
    conn.close()
