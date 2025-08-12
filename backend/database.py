
import os
import psycopg2
from psycopg2 import sql
import time

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    max_retries = 5
    retry_delay = 5  # seconds
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(
                dbname=os.environ.get("POSTGRES_DB"),
                user=os.environ.get("POSTGRES_USER"),
                password=os.environ.get("POSTGRES_PASSWORD"),
                host="postgres"  # This MUST match the service name in docker-compose.yml
            )
            return conn
        except psycopg2.OperationalError as e:
            print(f"Database connection failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Could not connect to the database. Exiting.")
                raise

def initialize_database():
    """
    Initializes the database by creating necessary tables if they don't exist.
    """
    print("Initializing database...")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Create the stock_prices table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS stock_prices (
                    id SERIAL PRIMARY KEY,
                    symbol VARCHAR(20) NOT NULL,
                    asset_type VARCHAR(10) NOT NULL, -- 'stock' or 'crypto'
                    price NUMERIC(15, 5) NOT NULL, -- Increased precision for crypto
                    timestamp BIGINT NOT NULL
                );
            """)
            # Create an index on symbol and timestamp for faster queries
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_stock_prices_symbol_timestamp 
                ON stock_prices (symbol, timestamp DESC);
            """)
            conn.commit()
        print("Table 'stock_prices' is ready.")
    finally:
        conn.close()

if __name__ == "__main__":
    # This allows us to run the script directly to initialize the DB.
    initialize_database()
