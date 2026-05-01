"""
Processing Service - Main Application
Consumes IoT data from Kafka, processes, and stores in PostgreSQL
Implements Database per Service pattern with event publishing
"""
import logging
import asyncio
import signal
import sys

from app.kafka.kafka_consumer import KafkaConsumerClient
from app.services.processing_service import ProcessingService
from app.services.outbox_processor import outbox_processor
from app.core.database import engine
from app.core.redis_publisher import redis_publisher
from app.kafka.event_publisher import event_publisher
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ProcessingServiceApp:
    """Main processing service orchestrator"""
    
    def __init__(self):
        self.processing_service = ProcessingService()
        self.kafka_consumer = KafkaConsumerClient(self.processing_service)
        self.running = False
    
    async def start(self):
        """Start the processing service"""
        logger.info("Starting Processing Service...")
        logger.info(f"Kafka Brokers: {settings.KAFKA_BOOTSTRAP_SERVERS}")
        logger.info(f"Kafka Topic: {settings.KAFKA_TOPIC_IOT_LOGS}")
        logger.info(f"Database: {settings.PROCESSING_DB_HOST}:{settings.PROCESSING_DB_PORT}/{settings.PROCESSING_DB_NAME}")
        logger.info(f"Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        logger.info(f"Event Publishing: {'Enabled' if settings.ENABLE_EVENT_PUBLISHING else 'Disabled'}")
        
        # Test database connection
        try:
            with engine.connect() as conn:
                logger.info("Processing database connection successful")
        except Exception as e:
            logger.error(f"Processing database connection failed: {e}")
            raise
        
        # Connect Redis publisher
        try:
            await redis_publisher.connect()
            logger.info("Redis publisher connected")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise
        
        self.running = True
        
        # Start Kafka consumer in background
        consumer_task = asyncio.create_task(self.kafka_consumer.start())
        
        # Start outbox processor in background
        outbox_task = None
        if settings.ENABLE_EVENT_PUBLISHING:
            outbox_task = asyncio.create_task(outbox_processor.start())
            logger.info("Outbox processor started")
        
        # Keep service running
        try:
            while self.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            consumer_task.cancel()
            if outbox_task:
                outbox_processor.stop()
                outbox_task.cancel()
            await self.stop()
    
    async def stop(self):
        """Stop the processing service"""
        logger.info("Stopping Processing Service...")
        self.running = False
        
        # Stop Kafka consumer
        self.kafka_consumer.stop()
        
        # Close Redis publisher
        await redis_publisher.disconnect()
        
        # Close event publisher
        event_publisher.close()
        
        logger.info("Processing Service stopped")


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    sys.exit(0)


async def main():
    """Main entry point"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start service
    service = ProcessingServiceApp()
    await service.start()


if __name__ == "__main__":
    asyncio.run(main())
