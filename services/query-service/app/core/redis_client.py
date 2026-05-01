"""
Redis client for caching
"""
import redis.asyncio as redis
import logging
from typing import Optional
import json

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client wrapper for caching operations"""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self._connect()
    
    def _connect(self):
        """Establish Redis connection"""
        try:
            self.client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )
            logger.info("Redis client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Redis client: {e}")
            self.client = None
    
    async def ping(self) -> bool:
        """Test Redis connection"""
        try:
            if self.client:
                await self.client.ping()
                return True
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
        return False
    
    async def get(self, key: str) -> Optional[str]:
        """
        Get value from Redis
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None
        """
        try:
            if self.client:
                value = await self.client.get(key)
                if value:
                    logger.debug(f"Cache hit: {key}")
                    return value
                logger.debug(f"Cache miss: {key}")
        except Exception as e:
            logger.error(f"Redis get error: {e}")
        return None
    
    async def set(self, key: str, value: str, ttl: int = None) -> bool:
        """
        Set value in Redis
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            Success status
        """
        try:
            if self.client:
                if ttl:
                    await self.client.setex(key, ttl, value)
                else:
                    await self.client.set(key, value)
                logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
                return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
        return False
    
    async def delete(self, key: str) -> bool:
        """
        Delete key from Redis
        
        Args:
            key: Cache key
            
        Returns:
            Success status
        """
        try:
            if self.client:
                await self.client.delete(key)
                logger.debug(f"Cache deleted: {key}")
                return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
        return False
    
    async def close(self):
        """Close Redis connection"""
        try:
            if self.client:
                await self.client.close()
                logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")


# Global Redis client instance
redis_client = RedisClient()
