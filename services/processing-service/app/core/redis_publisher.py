"""
Redis Publisher for real-time event broadcasting
"""
import redis.asyncio as redis
import logging
import json
from typing import Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisPublisher:
    """Redis publisher for broadcasting IoT events"""
    
    def __init__(self):
        self.client = None
    
    async def connect(self):
        """Establish Redis connection"""
        try:
            self.client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                decode_responses=True
            )
            await self.client.ping()
            logger.info("Redis publisher connected")
        except Exception as e:
            logger.error(f"Failed to connect Redis publisher: {e}")
            raise
    
    async def publish(self, data: Dict[str, Any]):
        """
        Publish event to Redis channel
        
        Args:
            data: Event data
        """
        if not self.client:
            logger.error("Redis publisher not connected")
            return
        
        try:
            message = json.dumps(data, default=str)
            await self.client.publish(settings.REDIS_CHANNEL, message)
            logger.debug(f"Published to channel {settings.REDIS_CHANNEL}")
        except Exception as e:
            logger.error(f"Error publishing to Redis: {e}")
    
    async def disconnect(self):
        """Close Redis connection"""
        try:
            if self.client:
                await self.client.close()
                logger.info("Redis publisher disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting Redis publisher: {e}")


# Global publisher instance
redis_publisher = RedisPublisher()
