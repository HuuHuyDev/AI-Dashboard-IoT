"""
Redis Client for Chatbot Service
Handles session management and SQL caching
"""
import redis.asyncio as redis
import logging
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Async Redis client for chatbot service"""
    
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
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None
    
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set value in Redis with optional TTL"""
        try:
            if ttl:
                return await self.client.setex(key, ttl, value)
            else:
                return await self.client.set(key, value)
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
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
    
    async def expire(self, name: str, time: int) -> bool:
        """Set expiration time"""
        try:
            return await self.client.expire(name, time)
        except Exception as e:
            logger.error(f"Redis EXPIRE error: {e}")
            return False
    
    async def rpush(self, name: str, *values) -> int:
        """Push values to list"""
        try:
            return await self.client.rpush(name, *values)
        except Exception as e:
            logger.error(f"Redis RPUSH error: {e}")
            return 0
    
    async def lrange(self, name: str, start: int, end: int) -> list:
        """Get list range"""
        try:
            return await self.client.lrange(name, start, end)
        except Exception as e:
            logger.error(f"Redis LRANGE error: {e}")
            return []


# Global Redis client instance
redis_client = RedisClient()
