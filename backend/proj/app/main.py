from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy import text
import logging

from .database import engine
from . import models
from .api import knn, trades, market, metrics, websocket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migrations():
    """Run database migrations for schema updates."""
    with engine.connect() as conn:
        # Check if score column exists in knn_results table
        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'knn_results' AND column_name = 'score'
        """))
        if not result.fetchone():
            logger.info("Adding 'score' column to knn_results table...")
            conn.execute(text("ALTER TABLE knn_results ADD COLUMN score FLOAT"))
            conn.commit()
            logger.info("Migration complete: added 'score' column")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    await websocket.start_redis_listener()
    yield
    # Shutdown
    await websocket.stop_redis_listener()


models.Base.metadata.create_all(bind=engine)
run_migrations()

app = FastAPI(title="Trader API", lifespan=lifespan)

# Include REST API routers
app.include_router(knn.router, prefix="/api", tags=["KNN"])
app.include_router(trades.router, prefix="/api", tags=["Trades"])
app.include_router(market.router, prefix="/api", tags=["Market"])
app.include_router(metrics.router, prefix="/api", tags=["Metrics"])

# Include WebSocket router
app.include_router(websocket.router, tags=["WebSocket"])


@app.get("/")
def read_root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to the Trader API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "knn": "/api/knn/top",
            "trades": "/api/trades",
            "market_hours": "/api/market-hours",
            "metrics": "/api/metrics",
            "health": "/api/health",
            "websocket": "/ws/predictions"
        }
    }
