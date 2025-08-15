
import os
import time
import redis
import database

def get_redis_connection():
    """Establishes a connection to Redis."""
    return redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

def process_data(db_conn):
    """
    Fetches the latest data for each symbol and creates virtual positions.
    """
    print("Processing data...")
    try:
        with db_conn.cursor() as cur:
            # Get the most recent timestamp for each symbol
            cur.execute("""
                SELECT symbol, asset_type, price, timestamp
                FROM (
                    SELECT *, ROW_NUMBER() OVER(PARTITION BY symbol ORDER BY timestamp DESC) as rn
                    FROM stock_prices
                ) t
                WHERE rn = 1;
            """)
            latest_prices = cur.fetchall()

            for symbol, asset_type, price, timestamp in latest_prices:
                # Create virtual long position
                save_training_data(db_conn, symbol, asset_type, 'long', price, timestamp)
                # Create virtual short position
                save_training_data(db_conn, symbol, asset_type, 'short', price, timestamp)
            
            db_conn.commit()
            print(f"Processed {len(latest_prices)} assets.")

    except Exception as e:
        print(f"Error processing data: {e}")
        db_conn.rollback()

def save_training_data(conn, symbol, asset_type, position_type, open_price, timestamp):
    """Saves a single training data record to the database."""
    order_fee = 5.00
    order_size = 100.00
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO training (symbol, asset_type, position_type, open_price, timestamp, order_fee, order_size)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (symbol, asset_type, position_type, open_price, timestamp, order_fee, order_size)
        )

def main():
    """
    Main loop for the trainer service.
    """
    print("Starting trainer service...")
    db_conn = database.get_db_connection()
    redis_conn = get_redis_connection()
    
    # Initialize database to ensure tables are created
    database.initialize_database()

    # Redis pub/sub setup
    pubsub = redis_conn.pubsub()
    pubsub.subscribe('data-fetched')

    print("Waiting for data-fetched message from Redis...")
    while True:
        message = pubsub.get_message()
        if message and message['type'] == 'message':
            print(f"Received message: {message['data']}")
            process_data(db_conn)
        time.sleep(1) # Prevent busy-waiting

if __name__ == "__main__":
    main()
