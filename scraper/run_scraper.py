#!/usr/bin/env python3
import time
import datetime
from feadparser import parseRSS
import db_connector

def run_scraper(init_db=True, close_db=True):
    """Run the scraper to fetch and store RSS feed items

    Args:
        init_db: Whether to initialize the database connection pool
        close_db: Whether to close the database connection pool after running
    """
    print(f"[{datetime.datetime.now()}] Starting RSS feed scraper...")

    # Initialize database connection if needed
    if init_db:
        try:
            db_connector.init_connection_pool()
        except Exception as e:
            print(f"[{datetime.datetime.now()}] Error initializing database connection: {e}")
            return []

    try:
        # Parse RSS feeds and store in database
        # We'll modify parseRSS to not initialize or close the connection pool
        # when called from here
        articles = parseRSS(manage_db_connection=False)
        print(f"[{datetime.datetime.now()}] Fetched {len(articles)} articles")

        # Articles are already saved to the database in parseRSS()
        # But we can log the count here
        print(f"[{datetime.datetime.now()}] Scraper run completed successfully")
        return articles

    except Exception as e:
        print(f"[{datetime.datetime.now()}] Error running scraper: {e}")
        return []
    finally:
        # Close database connection if needed
        if close_db:
            try:
                db_connector.close_connection_pool()
            except Exception as e:
                print(f"[{datetime.datetime.now()}] Error closing database connection: {e}")

if __name__ == "__main__":
    import sys

    # Run once by default
    run_once = True
    interval = 3600  # Default: 1 hour

    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--daemon":
            run_once = False
            if len(sys.argv) > 2:
                try:
                    interval = int(sys.argv[2])
                except ValueError:
                    print(f"Invalid interval: {sys.argv[2]}. Using default: 3600 seconds")

    if run_once:
        # For a single run, initialize and close the connection pool
        run_scraper(init_db=True, close_db=True)
    else:
        print(f"Running in daemon mode with interval of {interval} seconds")

        # In daemon mode, initialize the connection pool once
        try:
            db_connector.init_connection_pool()

            while True:
                try:
                    # Run the scraper without initializing or closing the connection pool
                    run_scraper(init_db=False, close_db=False)
                    print(f"Sleeping for {interval} seconds...")
                    time.sleep(interval)
                except KeyboardInterrupt:
                    print("Scraper daemon stopped by user")
                    break
                except Exception as e:
                    print(f"Error in scraper daemon: {e}")
                    # Sleep for a shorter time if there was an error
                    time.sleep(60)
        finally:
            # Make sure to close the connection pool when exiting
            try:
                db_connector.close_connection_pool()
                print("Database connection pool closed")
            except Exception as e:
                print(f"Error closing database connection pool: {e}")
