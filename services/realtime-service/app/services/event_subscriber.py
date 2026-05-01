"""
Event Subscriber - Subscribes to Redis Pub/Sub for IoT events
"""
import logging
import json
import asyncio

from app.core.redis_client import redis_client
from app.services.connection_manager import connection_manager
from app.services.event_buffer import event_buffer
from app.core.config import settings

logger = logging.getLogger(__name__)


class EventSubscriber:
    """Subscribes to IoT events via Redis Pub/Sub"""
    
    def __init__(self):
        self.running = False
        self.pubsub = None
    
    async def start(self):
        """Start subscribing to events"""
        self.running = True
        self.pubsub = redis_client.pubsub()
        
        try:
            await self.pubsub.subscribe(settings.REDIS_CHANNEL)
            logger.info(f"Subscribed to {settings.REDIS_CHANNEL} channel")
            
            while self.running:
                try:
                    message = await self.pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    
                    if message and message['type'] == 'message':
                        await self._handle_event(message['data'])
                    
                    await asyncio.sleep(0.01)
                    
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    
        except Exception as e:
            logger.error(f"Event subscriber error: {e}")
        finally:
            await self.stop()
    
    async def _handle_event(self, data: str):
        """
        Handle incoming event
        
        Args:
            data: Event data (JSON string)
        """
        try:
            event = json.loads(data)
            device_id = event.get('data', {}).get('device_id')
            
            if not device_id:
                logger.warning("Event missing device_id")
                return
            
            # Buffer event
            await event_buffer.buffer_event(device_id, event)
            
            # Broadcast to subscribers
            await connection_manager.broadcast_to_device(device_id, event)
            
            logger.debug(f"Processed event for device {device_id}")
            
        except Exception as e:
            logger.error(f"Error handling event: {e}")
    
    async def stop(self):
        """Stop event subscriber"""
        self.running = False
        if self.pubsub:
            await self.pubsub.unsubscribe(settings.REDIS_CHANNEL)
            await self.pubsub.close()
            logger.info("Event subscriber stopped")


event_subscriber = EventSubscriber()
