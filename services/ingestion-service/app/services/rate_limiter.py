"""
Rate Limiter Service
"""
import logging
from app.core.redis_client import redis_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiting using Redis"""
    
    def __init__(self):
        self.prefix = "ingestion:ratelimit"
    
    async def check_device_limit(self, device_id: str) -> bool:
        """Check if device is within rate limit"""
        try:
            key = f"{self.prefix}:device:{device_id}"
            count = await redis_client.client.incr(key)
            
            if count == 1:
                await redis_client.client.expire(key, 1)  # 1 second window
            
            if count > settings.RATE_LIMIT_PER_DEVICE:
                logger.warning(f"Device {device_id} exceeded rate limit: {count}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True  # Allow on error
    
    async def check_global_limit(self) -> bool:
        """Check global rate limit"""
        try:
            key = f"{self.prefix}:global"
            count = await redis_client.client.incr(key)
            
            if count == 1:
                await redis_client.client.expire(key, 1)  # 1 second window
            
            if count > settings.RATE_LIMIT_GLOBAL:
                logger.warning(f"Global rate limit exceeded: {count}")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Global rate limit check failed: {e}")
            return True  # Allow on error


# Global instance
rate_limiter = RateLimiter()
