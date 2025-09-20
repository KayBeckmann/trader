import os
import time
import json
import redis
import database

TRADE_ORDER_SIZE = float(os.environ.get("TRADE_ORDER_SIZE", "1000"))

def get_redis_connection():
    """Establishes a connection to Redis."""
    return redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

def open_trades(db_conn, symbols, position_type):
    """Opens new trades for a list of symbols."""
    print(f"Opening {position_type} trades for: {symbols}")
    for symbol in symbols:
        try:
            with db_conn.cursor() as cur:
                cur.execute("SELECT price FROM stock_prices WHERE symbol = %s ORDER BY timestamp DESC LIMIT 1", (symbol,))
                latest_price = cur.fetchone()

                if not latest_price:
                    print(f"Could not find a price for {symbol}. Trade not opened.")
                    continue

                open_price = latest_price[0]
                fee = 5.00
                open_timestamp = int(time.time())

                cur.execute("""
                    INSERT INTO trades (symbol, position_type, open_price, fee, open_timestamp, status)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (symbol, position_type, open_price, fee, open_timestamp, 'open'))
                print(f"Opened {position_type} trade for {symbol} at {open_price}")
            db_conn.commit()

        except Exception as e:
            print(f"Error opening trade for {symbol}: {e}")
            db_conn.rollback()

def add_trade_to_training_data(cur, symbol, pos_type, open_price, open_ts, close_price, order_size, fee, profit_loss):
    """Adds a closed trade to the training table."""
    try:
        # 1. Get asset_type from stock_prices table
        cur.execute("SELECT asset_type FROM stock_prices WHERE symbol = %s LIMIT 1", (symbol,))
        asset_type_row = cur.fetchone()
        if not asset_type_row:
            print(f"Could not find asset_type for {symbol}. Skipping training data insertion.")
            return
        asset_type = asset_type_row[0]

        # 2. Insert into training table using the realised close price and P/L
        cur.execute("""
            INSERT INTO training (symbol, asset_type, position_type, open_price, timestamp, order_fee, order_size, status, close_price, close_timestamp, profit_loss)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (symbol, asset_type, pos_type, open_price, open_ts, fee, order_size, 'closed', close_price, int(time.time()), profit_loss))
        print(f"Added closed trade for {symbol} to training data.")

    except Exception as e:
        print(f"Error adding trade to training data for {symbol}: {e}")


def check_and_close_trades(db_conn):
    """Checks and closes open trades based on SL, TP, or time."""
    # print("Checking for trades to close...")
    try:
        with db_conn.cursor() as cur:
            cur.execute("SELECT id, symbol, position_type, open_price, open_timestamp, fee FROM trades WHERE status = 'open'")
            open_trades = cur.fetchall()

            for trade in open_trades:
                trade_id, symbol, pos_type, open_price, open_ts, fee = trade
                
                cur.execute("SELECT price FROM stock_prices WHERE symbol = %s ORDER BY timestamp DESC LIMIT 1", (symbol,))
                current_price_row = cur.fetchone()
                if not current_price_row:
                    continue
                
                current_price = current_price_row[0]
                
                pnl_percentage = ((current_price - open_price) / open_price) * 100 if pos_type == 'long' else ((open_price - current_price) / open_price) * 100

                should_close = False
                if pnl_percentage <= -10: # Stop-Loss
                    print(f"Closing trade {trade_id} ({symbol} {pos_type}) due to Stop-Loss.")
                    should_close = True
                elif pnl_percentage >= 10: # Take-Profit
                    print(f"Closing trade {trade_id} ({symbol} {pos_type}) due to Take-Profit.")
                    should_close = True
                elif int(time.time()) - open_ts >= 7200: # 2-hour timeout
                    print(f"Closing trade {trade_id} ({symbol} {pos_type}) due to 2-hour timeout.")
                    should_close = True

                if should_close:
                    open_price = float(open_price)
                    current_price = float(current_price)
                    fee = float(fee)
                    quantity = TRADE_ORDER_SIZE / open_price if open_price else 0.0

                    if pos_type == 'long':
                        gross_pl = (current_price - open_price) * quantity
                    else:
                        gross_pl = (open_price - current_price) * quantity

                    profit_loss = gross_pl - fee
                    close_timestamp = int(time.time())
                    cur.execute("""
                        UPDATE trades
                        SET status = 'closed', close_price = %s, close_timestamp = %s, profit_loss = %s
                        WHERE id = %s
                    """, (current_price, close_timestamp, profit_loss, trade_id))
                    
                    # Add the closed trade to the training data table
                    add_trade_to_training_data(cur, symbol, pos_type, open_price, open_ts, current_price, TRADE_ORDER_SIZE, fee, profit_loss)


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
        message = pubsub.get_message()
        if message and message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                if 'long' in data:
                    open_trades(db_conn, data['long'], 'long')
                if 'short' in data:
                    open_trades(db_conn, data['short'], 'short')
            except (json.JSONDecodeError, KeyError) as e:
                print(f"Could not parse prediction message: {message['data']}. Error: {e}")

        check_and_close_trades(db_conn)
        time.sleep(5) # Check every 5 seconds

if __name__ == "__main__":
    main()
