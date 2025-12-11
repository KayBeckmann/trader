"""
Metrics and health check API endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
import redis
from datetime import datetime, timedelta

from ..database import get_db
from ..models import StockPrice, Trade, KNNResult

router = APIRouter()


def get_redis_client():
    """Get Redis client."""
    try:
        client = redis.Redis(host='redis', port=6379, db=0)
        client.ping()
        return client
    except Exception:
        return None


@router.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    """
    Returns health status and counters for the trading system.

    Includes:
    - Database and Redis connection status
    - Counts for prices, training data, and trades
    - Latest predictions info
    """
    # Check database connection
    db_status = "healthy"
    try:
        db.execute("SELECT 1")
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Check Redis connection
    redis_client = get_redis_client()
    redis_status = "healthy" if redis_client else "unhealthy"

    # Get counts
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    one_day_ago = now - timedelta(days=1)

    # Stock prices
    total_prices = db.query(func.count(StockPrice.id)).scalar() or 0
    prices_last_hour = db.query(func.count(StockPrice.id)).filter(
        StockPrice.timestamp >= one_hour_ago
    ).scalar() or 0
    prices_last_day = db.query(func.count(StockPrice.id)).filter(
        StockPrice.timestamp >= one_day_ago
    ).scalar() or 0

    # Unique symbols
    unique_symbols = db.query(func.count(func.distinct(StockPrice.symbol))).scalar() or 0

    # Trades
    total_trades = db.query(func.count(Trade.id)).scalar() or 0
    open_trades = db.query(func.count(Trade.id)).filter(Trade.status == 'open').scalar() or 0
    closed_trades = db.query(func.count(Trade.id)).filter(Trade.status == 'closed').scalar() or 0

    # Trade results
    winning_trades = db.query(func.count(Trade.id)).filter(Trade.result == 1).scalar() or 0
    losing_trades = db.query(func.count(Trade.id)).filter(Trade.result == -1).scalar() or 0
    neutral_trades = db.query(func.count(Trade.id)).filter(Trade.result == 0).scalar() or 0

    # Calculate win rate
    win_rate = 0.0
    if winning_trades + losing_trades > 0:
        win_rate = winning_trades / (winning_trades + losing_trades) * 100

    # Latest predictions
    latest_prediction_time = db.query(func.max(KNNResult.created_at)).scalar()
    prediction_count = 0
    if latest_prediction_time:
        prediction_count = db.query(func.count(KNNResult.id)).filter(
            KNNResult.created_at == latest_prediction_time
        ).scalar() or 0

    return {
        "status": "healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded",
        "timestamp": now.isoformat(),
        "connections": {
            "database": db_status,
            "redis": redis_status
        },
        "prices": {
            "total": total_prices,
            "last_hour": prices_last_hour,
            "last_24h": prices_last_day,
            "unique_symbols": unique_symbols
        },
        "trades": {
            "total": total_trades,
            "open": open_trades,
            "closed": closed_trades,
            "results": {
                "wins": winning_trades,
                "losses": losing_trades,
                "neutral": neutral_trades,
                "win_rate_percent": round(win_rate, 2)
            }
        },
        "predictions": {
            "latest_timestamp": latest_prediction_time.isoformat() if latest_prediction_time else None,
            "count": prediction_count
        }
    }


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Simple health check endpoint."""
    try:
        db.execute("SELECT 1")
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
