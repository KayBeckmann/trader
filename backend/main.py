from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import redis
import json
import asyncio
import database

app = FastAPI()

# Hardcoded market hours (UTC)
MARKET_OPEN_HOUR_UTC = 14
MARKET_CLOSE_HOUR_UTC = 21
MARKET_DAYS_UTC = [0, 1, 2, 3, 4]  # Monday to Friday

def get_redis_connection():
    """Establishes a connection to Redis."""
    # Note: For async pub/sub, redis-py requires a non-decoded connection
    return redis.Redis(host='redis', port=6379, db=0)


@app.get("/")
def read_root():
    return {"message": "Hello from Backend API Server"}


@app.get("/api/market-hours")
def get_market_hours():
    """Returns the stock market opening hours in UTC."""
    return {
        "open_hour_utc": MARKET_OPEN_HOUR_UTC,
        "close_hour_utc": MARKET_CLOSE_HOUR_UTC,
        "market_days_utc": MARKET_DAYS_UTC,
    }

@app.get("/api/predictions")
def get_predictions():
    """Returns the latest top 10 long/short predictions from Redis."""
    try:
        redis_conn = get_redis_connection()
        latest_predictions = redis_conn.get('latest_predictions')
        if latest_predictions:
            return json.loads(latest_predictions)
        else:
            return {"long": [], "short": []}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/trades")
def get_trades():
    """Returns all closed trades from the database for P/L visualization."""
    db_conn = None
    try:
        db_conn = database.get_db_connection()
        with db_conn.cursor() as cur:
            cur.execute("SELECT symbol, open_price, close_price, profit_loss, status, timestamp FROM trades WHERE status = 'closed'")
            trades = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
            return [dict(zip(columns, row)) for row in trades]
    except Exception as e:
        if db_conn:
            db_conn.rollback()
        return {"error": str(e)}

@app.websocket("/ws/predictions")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    redis_conn = get_redis_connection()
    pubsub = redis_conn.pubsub()
    pubsub.subscribe('predictions')
    try:
        while True:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1)
            if message:
                await websocket.send_text(message['data'].decode('utf-8'))
            await asyncio.sleep(0.1) # Prevent tight loop
    except WebSocketDisconnect:
        print("Client disconnected")
    finally:
        pubsub.unsubscribe('predictions')
