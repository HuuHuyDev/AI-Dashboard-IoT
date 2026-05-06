"""
Query Service - Main Application
Handles SQL query execution with caching and CQRS read model updates
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import asyncio

from app.controllers import query_controller
from app.core.config import settings
from app.core.database import engine
from app.core.redis_client import redis_client
from app.kafka.event_consumer import event_consumer
from app.services.read_model_service import ReadModelService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global event consumer task
event_consumer_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    global event_consumer_task
    
    logger.info("Starting Query Service...")
    logger.info(f"Database: {settings.QUERY_DB_HOST}:{settings.QUERY_DB_PORT}/{settings.QUERY_DB_NAME}")
    logger.info(f"Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    if settings.ENABLE_KAFKA_CONSUMER:
        logger.info(f"Kafka: {settings.KAFKA_BOOTSTRAP_SERVERS}")
    else:
        logger.info("Kafka consumer: disabled")
    
    # Test database connection
    try:
        with engine.connect() as conn:
            logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
    
    # Test Redis connection
    try:
        await redis_client.ping()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
    
    # Start event consumer (optional)
    if settings.ENABLE_KAFKA_CONSUMER:
        try:
            read_model_service = ReadModelService()
            event_consumer_task = asyncio.create_task(
                event_consumer.start(read_model_service)
            )
            logger.info("Event consumer started")
        except Exception as e:
            logger.error(f"Failed to start event consumer: {e}")
    
    yield
    
    logger.info("Shutting down Query Service...")
    
    # Stop event consumer
    if event_consumer_task:
        event_consumer.stop()
        event_consumer_task.cancel()
        try:
            await event_consumer_task
        except asyncio.CancelledError:
            logger.info("Event consumer stopped")
    
    await redis_client.close()


# Initialize FastAPI application
app = FastAPI(
    title="IoT Dashboard - Query Service",
    description="SQL query execution service with Redis caching",
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
    query_controller.router,
    prefix="/api/v1/query",
    tags=["query"]
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Query Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    db_healthy = False
    redis_healthy = False
    
    try:
        with engine.connect():
            db_healthy = True
    except:
        pass
    
    try:
        await redis_client.ping()
        redis_healthy = True
    except:
        pass
    
    return {
        "status": "healthy" if (db_healthy and redis_healthy) else "degraded",
        "service": "query-service",
        "database": "connected" if db_healthy else "disconnected",
        "redis": "connected" if redis_healthy else "disconnected"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8002,
        reload=True
    )
