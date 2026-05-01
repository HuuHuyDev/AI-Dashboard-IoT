"""
Retry Service - Handle failed messages
"""
import logging
import json
import asyncio
from datetime import datetime
from app.core.redis_client import redis_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class RetryService:
    """Retry failed messages with exponential backoff"""
    
    def __init__(self, kafka_producer):
        self.kafka_producer = kafka_producer
        self.prefix = "ingestion:retry"
        self.running = False
    
    async def add_failed_message(self, message: dict, error: str):
        """Add failed message to retry queue"""
        try:
            retry_data = {
                "message": message,
                "error": error,
                "timestamp": datetime.utcnow().isoformat(),
                "attempts": 0
            }
            
            await redis_client.client.lpush(
                f"{self.prefix}:queue",
                json.dumps(retry_data)
            )
            logger.info(f"Added message to retry queue: {message.get('device_id')}")
        except Exception as e:
            logger.error(f"Failed to add to retry queue: {e}")
    
    async def process_retry_queue(self):
        """Process retry queue with exponential backoff"""
        self.running = True
        
        while self.running:
            try:
                # Get message from queue
                data = await redis_client.client.rpop(f"{self.prefix}:queue")
                
                if not data:
                    await asyncio.sleep(5)
                    continue
                
                retry_data = json.loads(data)
                message = retry_data["message"]
                attempts = retry_data["attempts"]
                
                if attempts >= settings.MAX_RETRY_ATTEMPTS:
                    # Move to dead letter queue
                    await redis_client.client.lpush(
                        f"{self.prefix}:dead_letter",
                        json.dumps(retry_data)
                    )
                    logger.warning(f"Message moved to dead letter queue after {attempts} attempts")
                    continue
                
                # Try to send again
                try:
                    self.kafka_producer.send_message(message)
                    logger.info(f"Retry successful for message: {message.get('device_id')}")
                except Exception as e:
                    # Increment attempts and re-queue
                    retry_data["attempts"] = attempts + 1
                    retry_data["last_error"] = str(e)
                    
                    # Exponential backoff
                    backoff = settings.RETRY_BACKOFF_SECONDS * (2 ** attempts)
                    await asyncio.sleep(backoff)
                    
                    await redis_client.client.lpush(
                        f"{self.prefix}:queue",
                        json.dumps(retry_data)
                    )
                    logger.warning(f"Retry failed, re-queued with backoff {backoff}s")
                
            except Exception as e:
                logger.error(f"Error processing retry queue: {e}")
                await asyncio.sleep(5)
    
    def stop(self):
        """Stop retry processor"""
        self.running = False


# Global instance (will be initialized with kafka_producer)
retry_service = None
