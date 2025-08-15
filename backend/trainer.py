import os
import time
import redis
import database

def get_redis_connection():
    """Establishes a connection to Redis."""
    return redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

def open_training_positions(db_conn):
    """
    Fetches the latest data for each symbol and creates virtual positions.
    """
    print("Opening new training positions...")
    try:
        with db_conn.cursor() as cur:
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
                save_training_data(db_conn, symbol, asset_type, 'long', price, timestamp)
                save_training_data(db_conn, symbol, asset_type, 'short', price, timestamp)
            
            db_conn.commit()
            print(f"Opened {len(latest_prices) * 2} new training positions.")

    except Exception as e:
        print(f"Error opening training positions: {e}")
        db_conn.rollback()

def save_training_data(conn, symbol, asset_type, position_type, open_price, timestamp):
    """Saves a single training data record to the database."""
    order_fee = 5.00
    order_size = 100.00
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO training (symbol, asset_type, position_type, open_price, timestamp, order_fee, order_size, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (symbol, asset_type, position_type, open_price, timestamp, order_fee, order_size, 'open')
        )

def check_and_close_training_positions(db_conn):
    """Checks and closes open training positions based on SL, TP, or time."""
    print("Checking and closing training positions...")
    try:
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, symbol, position_type, open_price, timestamp, order_fee, order_size FROM training WHERE status = 'open'")
            open_positions = cur.fetchall()

            for pos in open_positions:
                pos_id, symbol, pos_type, open_price, open_ts, fee, size = pos
                
                cur.execute("SELECT price FROM stock_prices WHERE symbol = %s ORDER BY timestamp DESC LIMIT 1", (symbol,))
                current_price_row = cur.fetchone()
                if not current_price_row:
                    continue
                
                current_price = current_price_row[0]
                
                pnl_percentage = ((current_price - open_price) / open_price) * 100 if pos_type == 'long' else ((open_price - current_price) / open_price) * 100

                # Check for Stop-Loss, Take-Profit, or 1-hour timeout
                should_close = False
                if pnl_percentage <= -10: # Stop-Loss
                    print(f"Closing position {pos_id} ({symbol} {pos_type}) due to Stop-Loss.")
                    should_close = True
                elif pnl_percentage >= 10: # Take-Profit
                    print(f"Closing position {pos_id} ({symbol} {pos_type}) due to Take-Profit.")
                    should_close = True
                elif int(time.time()) - open_ts >= 3600: # 1-hour timeout
                    print(f"Closing position {pos_id} ({symbol} {pos_type}) due to 1-hour timeout.")
                    should_close = True

                if should_close:
                    profit_loss = (current_price - open_price - fee) if pos_type == 'long' else (open_price - current_price - fee)
                    close_timestamp = int(time.time())
                    cur.execute("""
                        UPDATE training
                        SET status = 'closed', close_price = %s, close_timestamp = %s, profit_loss = %s
                        WHERE id = %s
                    """, (current_price, close_timestamp, profit_loss, pos_id))

            db_conn.commit()

    except Exception as e:
        print(f"Error checking/closing training positions: {e}")
        db_conn.rollback()

def main():
    """Main loop for the trainer service."""
    print("Starting trainer service...")
    database.initialize_database()
    db_conn = database.get_db_connection()
    redis_conn = get_redis_connection()
    
    pubsub = redis_conn.pubsub()
    pubsub.subscribe('data-fetched')

    print("Waiting for data-fetched message from Redis...")
    while True:
        message = pubsub.get_message()
        if message and message['type'] == 'message':
            print(f"Received message: {message['data']}")
            open_training_positions(db_conn)
            check_and_close_training_positions(db_conn)
        time.sleep(1)

if __name__ == "__main__":
    main()