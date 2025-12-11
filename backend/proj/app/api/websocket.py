"""
WebSocket endpoint for real-time predictions.
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import redis.asyncio as redis
import asyncio
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        """Broadcast message to all connected clients."""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error sending message: {e}")
                disconnected.append(connection)

        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


async def redis_listener():
    """Listen for predictions on Redis and broadcast to WebSocket clients."""
    try:
        redis_client = redis.Redis(host='redis', port=6379, db=0)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe('predictions')
        logger.info("Started Redis listener for predictions channel")

        async for message in pubsub.listen():
            if message['type'] == 'message':
                data = message['data']
                if isinstance(data, bytes):
                    data = data.decode('utf-8')
                await manager.broadcast(data)
                logger.info("Broadcasted predictions to WebSocket clients")
    except Exception as e:
        logger.error(f"Redis listener error: {e}")
        await asyncio.sleep(5)  # Wait before retry


@router.websocket("/ws/predictions")
async def websocket_predictions(websocket: WebSocket):
    """
    WebSocket endpoint for real-time prediction updates.

    Clients connect to this endpoint to receive predictions
    as soon as they are published by the KNN worker.

    Message format: {"long": [...], "short": [...]}
    """
    await manager.connect(websocket)

    try:
        # Start Redis listener if not already running
        # This is a simplified approach - in production, use a background task
        while True:
            try:
                # Keep connection alive and wait for messages
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                # Echo back any received messages (for ping/pong)
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send heartbeat
                try:
                    await websocket.send_text(json.dumps({"type": "heartbeat"}))
                except Exception:
                    break
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


# Background task to be started with the app
_redis_task = None


async def start_redis_listener():
    """Start the Redis listener as a background task."""
    global _redis_task
    if _redis_task is None:
        _redis_task = asyncio.create_task(redis_listener())
        logger.info("Redis listener background task started")


async def stop_redis_listener():
    """Stop the Redis listener background task."""
    global _redis_task
    if _redis_task:
        _redis_task.cancel()
        try:
            await _redis_task
        except asyncio.CancelledError:
            pass
        _redis_task = None
        logger.info("Redis listener background task stopped")
