"""
Redis Client for Realtime Service
"""
import redis.asyncio as redis
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client for realtime service"""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True
            )
            await self.client.ping()
            logger.info(f"Connected to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()
            logger.info("Redis connection closed")
    
    async def ping(self) -> bool:
        """Test Redis connection"""
        try:
            return await self.client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
    
    async def hset(self, name: str, mapping: dict) -> int:
        """Set hash fields"""
        try:
            return await self.client.hset(name, mapping=mapping)
        except Exception as e:
            logger.error(f"Redis HSET error: {e}")
            return 0
    
    async def hgetall(self, name: str) -> dict:
        """Get all hash fields"""
        try:
            return await self.client.hgetall(name)
        except Exception as e:
            logger.error(f"Redis HGETALL error: {e}")
            return {}
    
    async def sadd(self, name: str, *values) -> int:
        """Add to set"""
        try:
            return await self.client.sadd(name, *values)
        except Exception as e:
            logger.error(f"Redis SADD error: {e}")
            return 0
    
    async def smembers(self, name: str) -> set:
        """Get set members"""
        try:
            return await self.client.smembers(name)
        except Exception as e:
            logger.error(f"Redis SMEMBERS error: {e}")
            return set()
    
    async def srem(self, name: str, *values) -> int:
        """Remove from set"""
        try:
            return await self.client.srem(name, *values)
        except Exception as e:
            logger.error(f"Redis SREM error: {e}")
            return 0
    
    async def lpush(self, name: str, *values) -> int:
        """Push to list"""
        try:
            return await self.client.lpush(name, *values)
        except Exception as e:
            logger.error(f"Redis LPUSH error: {e}")
            return 0
    
    async def ltrim(self, name: str, start: int, end: int) -> bool:
        """Trim list"""
        try:
            return await self.client.ltrim(name, start, end)
        except Exception as e:
            logger.error(f"Redis LTRIM error: {e}")
            return False
    
    async def lrange(self, name: str, start: int, end: int) -> list:
        """Get list range"""
        try:
            return await self.client.lrange(name, start, end)
        except Exception as e:
            logger.error(f"Redis LRANGE error: {e}")
            return []
    
    def pubsub(self):
        """Get pubsub instance"""
        return self.client.pubsub()


redis_client = RedisClient()
