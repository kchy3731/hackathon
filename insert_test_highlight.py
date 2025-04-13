import psycopg2
from datetime import datetime

# Connect to the database
conn = psycopg2.connect(
    "dbname=banan user=timeframe_webserver password=1234 host=localhost"
)

try:
    with conn:
        with conn.cursor() as cur:
            # Insert a test highlight
            cur.execute("""
                INSERT INTO highlight (timestamp, headline, body, "user")
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (
                datetime.now(),
                "AI-Generated Test Headline: Major Technology Breakthrough Announced",
                "Researchers have announced a significant breakthrough in quantum computing technology that could revolutionize data processing capabilities. The new approach combines traditional silicon-based hardware with novel quantum algorithms, potentially solving complex problems in minutes that would take conventional computers years to process. Industry experts are calling this development a potential game-changer for fields ranging from medicine to climate science.",
                'wdbros@gmail.com'
            ))
            highlight_id = cur.fetchone()[0]
            print(f"Test highlight inserted successfully with ID: {highlight_id}")
except Exception as e:
    print(f"Error: {str(e)}")
finally:
    conn.close()
