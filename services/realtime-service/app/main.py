"""
Realtime Service - Main Application
Handles WebSocket connections and real-time data streaming
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio

from app.controllers import websocket_controller
from app.core.config import settings
from app.core.redis_client import redis_client
from app.services.event_subscriber import event_subscriber
from app.services.connection_manager import connection_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Background task for Redis listener
redis_listener_task = None


async def redis_message_handler(channel: str, message: dict):
    """
    Handle messages from Redis and broadcast to WebSocket clients
    
    Args:
        channel: Redis channel name
        message: Message data from Redis
    """
    logger.debug(f"Received Redis message from {channel}: {message}")
    await connection_manager.broadcast({
        "type": "iot_event",
        "channel": channel,
        "data": message
    })


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    global redis_listener_task
    
    logger.info("Starting Realtime Service...")
    logger.info(f"Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    logger.info(f"Redis Channels: {settings.REDIS_CHANNELS}")
    
    # Connect to Redis
    try:
        await redis_client.connect()
        logger.info("Redis client connected")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
    
    # Start event subscriber
    try:
        redis_listener_task = asyncio.create_task(
            event_subscriber.start(redis_message_handler)
        )
        logger.info("Event subscriber started")
    except Exception as e:
        logger.error(f"Failed to start event subscriber: {e}")
    
    yield
    
    logger.info("Shutting down Realtime Service...")
    
    # Stop event subscriber
    if redis_listener_task:
        redis_listener_task.cancel()
        try:
            await redis_listener_task
        except asyncio.CancelledError:
            pass
    
    # Disconnect from Redis
    await redis_client.disconnect()
    logger.info("Redis client disconnected")


# Initialize FastAPI application
app = FastAPI(
    title="IoT Dashboard - Realtime Service",
    description="WebSocket service for real-time IoT data streaming",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    websocket_controller.router,
    prefix="/api/v1/realtime",
    tags=["realtime"]
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Realtime Service",
        "version": "1.0.0",
        "status": "running",
        "active_connections": connection_manager.get_connection_count()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "realtime-service",
        "active_connections": connection_manager.get_connection_count(),
        "redis_connected": redis_client.is_connected()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8003,
        reload=True
    )
