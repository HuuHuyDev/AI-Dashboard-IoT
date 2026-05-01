"""
Outbox Processor - Processes outbox events and publishes to Kafka
Implements reliable event publishing using Transactional Outbox Pattern
"""
import logging
import asyncio
from typing import List, Dict, Any

from app.core.database import SessionLocal
from app.repositories.log_repository import LogRepository
from app.kafka.event_publisher import event_publisher
from app.core.config import settings

logger = logging.getLogger(__name__)


class OutboxProcessor:
    """Processes outbox events and publishes to Kafka"""
    
    def __init__(self):
        self.running = False
        self.poll_interval = 5  # seconds
    
    async def start(self):
        """Start outbox processor"""
        self.running = True
        logger.info("Starting outbox processor...")
        
        while self.running:
            try:
                await self.process_outbox_events()
                await asyncio.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error in outbox processor: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)
    
    def stop(self):
        """Stop outbox processor"""
        self.running = False
        logger.info("Stopping outbox processor...")
    
    async def process_outbox_events(self):
        """Process unpublished events from outbox"""
        db = SessionLocal()
        try:
            repository = LogRepository(db)
            
            # Get unpublished events
            events = repository.get_unpublished_events(limit=100)
            
            if not events:
                return
            
            logger.info(f"Processing {len(events)} outbox events")
            
            for event in events:
                try:
                    # Publish event to Kafka
                    success = self._publish_event(event)
                    
                    if success:
                        # Mark as published
                        repository.mark_event_published(event['event_id'])
                        logger.debug(f"Published event: {event['event_id']}")
                    else:
                        # Increment retry count
                        repository.increment_event_retry(
                            event['event_id'],
                            "Failed to publish to Kafka"
                        )
                        logger.warning(f"Failed to publish event: {event['event_id']}")
                
                except Exception as e:
                    logger.error(f"Error processing event {event['event_id']}: {e}")
                    repository.increment_event_retry(
                        event['event_id'],
                        str(e)
                    )
        
        finally:
            db.close()
    
    def _publish_event(self, event: Dict[str, Any]) -> bool:
        """
        Publish event to Kafka
        
        Args:
            event: Event data from outbox
            
        Returns:
            Success status
        """
        try:
            return event_publisher.publish_event(
                event_type=event['event_type'],
                aggregate_type=event['aggregate_type'],
                aggregate_id=event['aggregate_id'],
                data=event['payload'],
                correlation_id=event['metadata'].get('correlation_id')
            )
        except Exception as e:
            logger.error(f"Error publishing event: {e}")
            return False


# Global outbox processor instance
outbox_processor = OutboxProcessor()
