from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import redis
import json
import asyncio
import database
from datetime import datetime, time

app = FastAPI()

# Hardcoded market hours (UTC)
MARKET_OPEN_HOUR_UTC = 13
MARKET_OPEN_MINUTE_UTC = 30
MARKET_CLOSE_HOUR_UTC = 20
MARKET_CLOSE_MINUTE_UTC = 0
MARKET_DAYS_UTC = [0, 1, 2, 3, 4]  # Monday to Friday

def get_redis_connection():
    """Establishes a connection to Redis."""
    # Use decoded responses for consistency with other services
    return redis.Redis(host='redis', port=6379, db=0, decode_responses=True)


@app.get("/")
def read_root():
    return {"message": "Hello from Backend API Server"}


@app.get("/api/market-hours")
def get_market_hours():
    """Returns the stock market opening hours in UTC."""
    return {
        "open_hour_utc": MARKET_OPEN_HOUR_UTC,
        "open_minute_utc": MARKET_OPEN_MINUTE_UTC,
        "close_hour_utc": MARKET_CLOSE_HOUR_UTC,
        "close_minute_utc": MARKET_CLOSE_MINUTE_UTC,
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

def is_market_open_now():
    """Determine if the market is currently open based on UTC time and configured days/hours."""
    now = datetime.utcnow()
    if now.weekday() not in MARKET_DAYS_UTC:
        return False
    open_t = time(MARKET_OPEN_HOUR_UTC, MARKET_OPEN_MINUTE_UTC)
    close_t = time(MARKET_CLOSE_HOUR_UTC, MARKET_CLOSE_MINUTE_UTC)
    return open_t <= now.time() < close_t

@app.get("/api/metrics")
def get_metrics():
    """Return basic system metrics and health information."""
    metrics = {
        "market_open": is_market_open_now(),
        "database": {"ok": False},
        "redis": {"ok": False},
        "stock_prices": {},
        "training": {},
        "trades": {},
        "predictions": {},
    }

    # Database metrics
    db_conn = None
    try:
        db_conn = database.get_db_connection()
        with db_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM stock_prices")
            total_prices = cur.fetchone()[0]
            cur.execute("SELECT COUNT(DISTINCT symbol) FROM stock_prices")
            symbol_count = cur.fetchone()[0]
            cur.execute("SELECT MAX(timestamp) FROM stock_prices")
            last_price_ts = cur.fetchone()[0]

            cur.execute("SELECT status, COUNT(*) FROM training GROUP BY status")
            training_counts = {row[0]: row[1] for row in cur.fetchall()}

            cur.execute("SELECT status, COUNT(*) FROM trades GROUP BY status")
            trade_counts = {row[0]: row[1] for row in cur.fetchall()}
            cur.execute("SELECT MAX(close_timestamp) FROM trades WHERE status = 'closed'")
            last_close_ts = cur.fetchone()[0]

            metrics["database"]["ok"] = True
            metrics["stock_prices"] = {
                "total": total_prices,
                "symbols": symbol_count,
                "last_timestamp": last_price_ts,
                "last_timestamp_iso": datetime.utcfromtimestamp(last_price_ts).isoformat() if last_price_ts else None,
            }
            metrics["training"] = {
                "open": training_counts.get('open', 0),
                "closed": training_counts.get('closed', 0),
                "processed": training_counts.get('processed', 0),
            }
            metrics["trades"] = {
                "open": trade_counts.get('open', 0),
                "closed": trade_counts.get('closed', 0),
                "last_closed_timestamp": last_close_ts,
                "last_closed_timestamp_iso": datetime.utcfromtimestamp(last_close_ts).isoformat() if last_close_ts else None,
            }
    except Exception as e:
        metrics["database"]["error"] = str(e)
    finally:
        if db_conn:
            db_conn.close()

    # Redis / predictions metrics
    try:
        redis_conn = get_redis_connection()
        redis_conn.ping()
        metrics["redis"]["ok"] = True
        latest_predictions = redis_conn.get('latest_predictions')
        latest_ts = redis_conn.get('latest_predictions_ts')
        if latest_predictions:
            try:
                payload = json.loads(latest_predictions)
            except Exception:
                payload = {"long": [], "short": []}
        else:
            payload = {"long": [], "short": []}
        long_len = len(payload.get('long', []))
        short_len = len(payload.get('short', []))
        metrics["predictions"] = {
            "long_count": long_len,
            "short_count": short_len,
            "last_published_ts": int(latest_ts) if latest_ts else None,
            "last_published_iso": datetime.utcfromtimestamp(int(latest_ts)).isoformat() if latest_ts else None,
        }
    except Exception as e:
        metrics["redis"]["error"] = str(e)

    return metrics

@app.get("/api/trades")
def get_trades():
    """Returns all closed trades from the database for P/L visualization."""
    db_conn = None
    try:
        db_conn = database.get_db_connection()
        with db_conn.cursor() as cur:
            cur.execute("SELECT symbol, open_price, close_price, profit_loss, status, close_timestamp AS timestamp FROM trades WHERE status = 'closed'")
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
                # 'predictions' payloads are JSON strings already
                await websocket.send_text(message['data'])
            await asyncio.sleep(0.1) # Prevent tight loop
    except WebSocketDisconnect:
        print("Client disconnected")
    finally:
        pubsub.unsubscribe('predictions')
