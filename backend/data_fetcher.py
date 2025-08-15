import os
import time
import random
from datetime import datetime
import pytz

import database

# Define major stock market hours in UTC
# Example: NYSE 9:30 AM to 4:00 PM EST
# EST is UTC-5, EDT (daylight saving) is UTC-4. We'll use a simple approximation.
MARKET_OPEN_HOUR_UTC = 14  # 13:30 UTC -> 9:30 AM EDT
MARKET_CLOSE_HOUR_UTC = 21 # 20:00 UTC -> 4:00 PM EDT
MARKET_DAYS_UTC = [0, 1, 2, 3, 4]  # Monday to Friday

def is_market_open():
    """Checks if the stock market is currently open."""
    now_utc = datetime.now(pytz.utc)
    if now_utc.weekday() not in MARKET_DAYS_UTC:
        return False  # Market is closed on weekends
    if MARKET_OPEN_HOUR_UTC <= now_utc.hour < MARKET_CLOSE_HOUR_UTC:
        return True
    return False

def get_assets_from_file():
    """Reads the list of assets and their types from stocks.txt."""
    assets = []
    # The file is mounted in the same working directory in the container.
    try:
        with open("stocks.txt", "r") as f:
            for line in f:
                line = line.strip()
                if line and ',' in line:
                    symbol, asset_type = line.split(',')
                    assets.append((symbol.strip(), asset_type.strip()))
    except FileNotFoundError:
        print("Error: stocks.txt not found. Please create it.")
    return assets

def fetch_price_from_api(symbol):
    """
    Placeholder function to simulate fetching a price from an API.
    In a real application, this would make a call to a financial data provider.
    """
    # Simulate price fluctuation
    price = random.uniform(100, 500)
    print(f"Fetched (simulated) price for {symbol}: {price:.2f}")
    return price

def save_price_to_db(conn, symbol, asset_type, price, timestamp):
    """Saves a single price record to the database."""
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO stock_prices (symbol, asset_type, price, timestamp)
               VALUES (%s, %s, %s, %s)""",
            (symbol, asset_type, price, timestamp)
        )

import redis

def get_redis_connection():
    """Establishes a connection to Redis."""
    return redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

def main_loop():
    """
    The main loop for the data fetcher service.
    """
    print("Starting data fetcher service...")
    assets = get_assets_from_file()
    if not assets:
        print("No assets found in stocks.txt. Exiting.")
        return

    db_conn = database.get_db_connection()
    redis_conn = get_redis_connection()

    while True:
        print("--- New fetch cycle --- ")
        market_is_open = is_market_open()
        if market_is_open:
            print("Market is OPEN")
        else:
            print("Market is CLOSED")

        for symbol, asset_type in assets:
            try:
                fetch = False
                if asset_type == 'crypto':
                    fetch = True
                elif asset_type == 'stock' and market_is_open:
                    fetch = True

                if fetch:
                    price = fetch_price_from_api(symbol)
                    unix_timestamp = int(time.time())
                    save_price_to_db(db_conn, symbol, asset_type, price, unix_timestamp)
                    db_conn.commit()

            except Exception as e:
                print(f"Error processing {symbol}: {e}")
                db_conn.rollback() # Rollback on error for this asset

        # Publish message to Redis
        try:
            redis_conn.publish('data-fetched', 'true')
            print("Published data-fetched message to Redis.")
        except Exception as e:
            print(f"Error publishing to Redis: {e}")

        print(f"Cycle finished. Waiting for 5 minutes...")
        time.sleep(300) # Wait for 5 minutes

if __name__ == "__main__":
    # 1. Initialize the database (create tables if they don't exist)
    database.initialize_database()

    # 2. Start the main data fetching loop
    main_loop()