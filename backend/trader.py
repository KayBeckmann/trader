
import os
import time
import json
import redis
import database

def get_redis_connection():
    """Establishes a connection to Redis."""
    return redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

def open_trade(db_conn, symbol, position_type):
    """Opens a new trade in the database."""
    print(f"Opening a {position_type} trade for {symbol}...")
    try:
        with db_conn.cursor() as cur:
            # Get the latest price for the symbol
            cur.execute("""
                SELECT price FROM stock_prices 
                WHERE symbol = %s ORDER BY timestamp DESC LIMIT 1
            """, (symbol,))
            latest_price = cur.fetchone()

            if not latest_price:
                print(f"Could not find a price for {symbol}. Trade not opened.")
                return

            open_price = latest_price[0]
            fee = 5.00
            open_timestamp = int(time.time())

            cur.execute("""
                INSERT INTO trades (symbol, position_type, open_price, fee, open_timestamp, status)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (symbol, position_type, open_price, fee, open_timestamp, 'open'))
            db_conn.commit()
            print(f"Opened {position_type} trade for {symbol} at {open_price}")

    except Exception as e:
        print(f"Error opening trade: {e}")
        db_conn.rollback()

def check_and_close_trades(db_conn):
    """Checks for open trades and closes them after a fixed time (e.g., 1 hour)."""
    print("Checking for trades to close...")
    try:
        with db_conn.cursor() as cur:
            one_hour_ago = int(time.time()) - 3600
            cur.execute("SELECT id, symbol, position_type, open_price, fee FROM trades WHERE status = 'open' AND open_timestamp <= %s", (one_hour_ago,))
            open_trades = cur.fetchall()

            for trade in open_trades:
                trade_id, symbol, position_type, open_price, fee = trade
                
                # Get the current price to close the trade
                cur.execute("SELECT price FROM stock_prices WHERE symbol = %s ORDER BY timestamp DESC LIMIT 1", (symbol,))
                current_price_row = cur.fetchone()
                if not current_price_row:
                    print(f"Could not find current price for {symbol} to close trade {trade_id}. Skipping.")
                    continue
                
                close_price = current_price_row[0]
                close_timestamp = int(time.time())

                # Calculate profit/loss
                if position_type == 'long':
                    profit_loss = (close_price - open_price) - fee
                else: # short
                    profit_loss = (open_price - close_price) - fee

                # Update the trade record
                cur.execute("""
                    UPDATE trades
                    SET close_price = %s, profit_loss = %s, close_timestamp = %s, status = 'closed'
                    WHERE id = %s
                """, (close_price, profit_loss, close_timestamp, trade_id))
                print(f"Closed trade {trade_id} for {symbol}. P/L: {profit_loss:.2f}")

            db_conn.commit()

    except Exception as e:
        print(f"Error closing trades: {e}")
        db_conn.rollback()

def main():
    """Main loop for the trader service."""
    print("Starting trader service...")
    database.initialize_database()
    db_conn = database.get_db_connection()
    redis_conn = get_redis_connection()

    pubsub = redis_conn.pubsub()
    pubsub.subscribe('predictions')
    print("Subscribed to 'predictions' channel.")

    while True:
        # Listen for prediction messages
        message = pubsub.get_message()
        if message and message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                symbol = data['symbol']
                prediction = data['prediction']
                print(f"Received prediction: {prediction} for {symbol}")
                open_trade(db_conn, symbol, prediction)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Could not parse prediction message: {message['data']}. Error: {e}")

        # Periodically check for trades to close
        check_and_close_trades(db_conn)
        
        time.sleep(1) # Sleep to prevent busy-waiting

if __name__ == "__main__":
    main()
