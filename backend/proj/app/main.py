from fastapi import FastAPI
from contextlib import asynccontextmanager

from .database import engine
from . import models
from .api import knn, trades, market, metrics, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    await websocket.start_redis_listener()
    yield
    # Shutdown
    await websocket.stop_redis_listener()


models.Base.metadata.create_all(bind=engine)

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
