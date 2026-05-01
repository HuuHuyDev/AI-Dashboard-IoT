"""
Event Buffer - Stores recent events for new connections
"""
import logging
import json
from typing import List, Dict, Any

from app.core.redis_client import redis_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class EventBuffer:
    """Buffers recent events in Redis"""
    
    def __init__(self):
        self.buffer_size = settings.EVENT_BUFFER_SIZE
    
    async def buffer_event(self, device_id: str, event: Dict[str, Any]):
        """
        Buffer event for device
        
        Args:
            device_id: Device ID
            event: Event data
        """
        try:
            # Add to buffer
            await redis_client.lpush(
                f"event_buffer:{device_id}",
                json.dumps(event)
            )
            
            # Trim to buffer size
            await redis_client.ltrim(
                f"event_buffer:{device_id}",
                0,
                self.buffer_size - 1
            )
            
            logger.debug(f"Buffered event for device {device_id}")
            
        except Exception as e:
            logger.error(f"Error buffering event: {e}")
    
    async def get_recent_events(self, device_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent events for device
        
        Args:
            device_id: Device ID
            limit: Maximum number of events to return
            
        Returns:
            List of recent events
        """
        try:
            events = await redis_client.lrange(
                f"event_buffer:{device_id}",
                0,
                limit - 1
            )
            
            return [json.loads(event) for event in events]
            
        except Exception as e:
            logger.error(f"Error getting recent events: {e}")
            return []


event_buffer = EventBuffer()
