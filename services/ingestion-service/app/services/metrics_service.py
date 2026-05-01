"""
Metrics Service - Track ingestion metrics
"""
import logging
from datetime import datetime
from app.core.redis_client import redis_client

logger = logging.getLogger(__name__)


class MetricsService:
    """Track ingestion metrics in Redis"""
    
    def __init__(self):
        self.prefix = "ingestion:metrics"
    
    async def increment_received(self, device_id: str = None):
        """Increment messages received counter"""
        try:
            await redis_client.client.incr(f"{self.prefix}:received:total")
            if device_id:
                await redis_client.client.incr(f"{self.prefix}:received:device:{device_id}")
        except Exception as e:
            logger.error(f"Failed to increment received: {e}")
    
    async def increment_sent(self, device_id: str = None):
        """Increment messages sent to Kafka counter"""
        try:
            await redis_client.client.incr(f"{self.prefix}:sent:total")
            if device_id:
                await redis_client.client.incr(f"{self.prefix}:sent:device:{device_id}")
        except Exception as e:
            logger.error(f"Failed to increment sent: {e}")
    
    async def increment_failed(self, device_id: str = None):
        """Increment failed messages counter"""
        try:
            await redis_client.client.incr(f"{self.prefix}:failed:total")
            if device_id:
                await redis_client.client.incr(f"{self.prefix}:failed:device:{device_id}")
        except Exception as e:
            logger.error(f"Failed to increment failed: {e}")
    
    async def record_processing_time(self, duration_ms: float):
        """Record message processing time"""
        try:
            await redis_client.client.lpush(f"{self.prefix}:processing_time", duration_ms)
            await redis_client.client.ltrim(f"{self.prefix}:processing_time", 0, 999)
        except Exception as e:
            logger.error(f"Failed to record processing time: {e}")
    
    async def get_metrics(self) -> dict:
        """Get current metrics"""
        try:
            received = await redis_client.client.get(f"{self.prefix}:received:total") or 0
            sent = await redis_client.client.get(f"{self.prefix}:sent:total") or 0
            failed = await redis_client.client.get(f"{self.prefix}:failed:total") or 0
            
            return {
                "received": int(received),
                "sent": int(sent),
                "failed": int(failed),
                "success_rate": (int(sent) / int(received) * 100) if int(received) > 0 else 0
            }
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return {}


# Global instance
metrics_service = MetricsService()
