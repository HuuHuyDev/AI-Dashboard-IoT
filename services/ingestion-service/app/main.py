"""
Ingestion Service - Main Application
Receives IoT data from MQTT and forwards to Kafka
"""
import logging
import asyncio
import signal
import sys

from app.mqtt.mqtt_consumer import MQTTConsumer
from app.kafka.kafka_producer import KafkaProducerClient
from app.core.config import settings
from app.core.redis_client import redis_client
from app.services.metrics_service import metrics_service
from app.services.rate_limiter import rate_limiter
from app.services.retry_service import RetryService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class IngestionService:
    """Main ingestion service orchestrator"""
    
    def __init__(self):
        self.kafka_producer = KafkaProducerClient()
        self.retry_service = None
        self.mqtt_consumer = None
        self.retry_task = None
        self.running = False
    
    async def start(self):
        """Start the ingestion service"""
        logger.info("Starting Ingestion Service...")
        logger.info(f"MQTT Broker: {settings.MQTT_BROKER}:{settings.MQTT_PORT}")
        logger.info(f"MQTT Topic: {settings.MQTT_TOPIC}")
        logger.info(f"Kafka Brokers: {settings.KAFKA_BOOTSTRAP_SERVERS}")
        logger.info(f"Kafka Topic: {settings.KAFKA_TOPIC_IOT_LOGS}")
        logger.info(f"Redis: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        
        self.running = True
        
        # Connect to Redis
        try:
            await redis_client.connect()
            logger.info("Redis connected")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
        
        # Initialize retry service
        self.retry_service = RetryService(self.kafka_producer)
        
        # Start retry processor
        self.retry_task = asyncio.create_task(self.retry_service.process_retry_queue())
        logger.info("Retry service started")
        
        # Initialize MQTT consumer with services
        self.mqtt_consumer = MQTTConsumer(
            self.kafka_producer,
            metrics_service=metrics_service,
            rate_limiter=rate_limiter,
            retry_service=self.retry_service
        )
        
        # Start MQTT consumer
        self.mqtt_consumer.start()
        
        # Keep service running
        try:
            while self.running:
                # Log metrics every 60 seconds
                await asyncio.sleep(60)
                metrics = await metrics_service.get_metrics()
                logger.info(f"Metrics: {metrics}")
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the ingestion service"""
        logger.info("Stopping Ingestion Service...")
        self.running = False
        
        # Stop MQTT consumer
        if self.mqtt_consumer:
            self.mqtt_consumer.stop()
        
        # Stop retry service
        if self.retry_service:
            self.retry_service.stop()
        if self.retry_task:
            self.retry_task.cancel()
            try:
                await self.retry_task
            except asyncio.CancelledError:
                pass
        
        # Close Kafka producer
        self.kafka_producer.close()
        
        # Disconnect Redis
        await redis_client.disconnect()
        
        logger.info("Ingestion Service stopped")


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
    service = IngestionService()
    await service.start()


if __name__ == "__main__":
    asyncio.run(main())
