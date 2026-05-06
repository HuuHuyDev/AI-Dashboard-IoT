"""
Chatbot Service - Main Application
Handles AI-powered natural language queries for IoT data
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.controllers import chatbot_controller
from app.core.config import settings
from app.core.redis_client import redis_client
from app.mcp.database import mcp_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    logger.info("Starting Chatbot Service...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
    logger.info(f"Google Gemini API configured: {bool(settings.GEMINI_API_KEY)}")
    logger.info(f"Gemini Model: {settings.GEMINI_MODEL}")
    
    # Connect to Redis
    try:
        await redis_client.connect()
        logger.info("Redis connection successful")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
    
    # Connect to MCP Database
    try:
        await mcp_database.connect()
        logger.info("MCP Database connection successful")
    except Exception as e:
        logger.error(f"MCP Database connection failed: {e}")
    
    yield
    
    logger.info("Shutting down Chatbot Service...")
    await redis_client.close()
    await mcp_database.close()


# Initialize FastAPI application
app = FastAPI(
    title="IoT Dashboard - Chatbot Service",
    description="AI-powered chatbot service for natural language IoT data queries",
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
    chatbot_controller.router,
    prefix="/api/v1/chatbot",
    tags=["chatbot"]
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Chatbot Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    redis_healthy = await redis_client.ping()
    
    return {
        "status": "healthy" if redis_healthy else "degraded",
        "service": "chatbot-service",
        "redis": "connected" if redis_healthy else "disconnected"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
