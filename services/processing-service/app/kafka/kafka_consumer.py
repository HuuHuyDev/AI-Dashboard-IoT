"""
Kafka Consumer - Consumes IoT data from Kafka topic
"""
from kafka import KafkaConsumer
from kafka.errors import KafkaError
import logging
import json
import asyncio
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class KafkaConsumerClient:
    """Kafka consumer for receiving IoT data"""
    
    def __init__(self, processing_service):
        self.processing_service = processing_service
        self.consumer: Optional[KafkaConsumer] = None
        self.running = False
        self._connect()
    
    def _connect(self):
        """Establish Kafka consumer connection"""
        try:
            self.consumer = KafkaConsumer(
                settings.KAFKA_TOPIC_IOT_LOGS,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=settings.KAFKA_GROUP_ID,
                auto_offset_reset=settings.KAFKA_AUTO_OFFSET_RESET,
                enable_auto_commit=True,
                auto_commit_interval_ms=1000,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                max_poll_records=settings.BATCH_SIZE,
                session_timeout_ms=30000,
                heartbeat_interval_ms=10000
            )
            logger.info(f"Kafka consumer connected to {settings.KAFKA_BOOTSTRAP_SERVERS}")
            logger.info(f"Subscribed to topic: {settings.KAFKA_TOPIC_IOT_LOGS}")
        except Exception as e:
            logger.error(f"Failed to connect Kafka consumer: {e}")
            raise
    
    async def start(self):
        """Start consuming messages from Kafka"""
        if not self.consumer:
            logger.error("Kafka consumer not initialized")
            return
        
        self.running = True
        logger.info("Starting Kafka consumer...")
        
        try:
            while self.running:
                # Poll for messages
                messages = self.consumer.poll(timeout_ms=1000)
                
                if not messages:
                    await asyncio.sleep(0.1)
                    continue
                
                # Process messages
                for topic_partition, records in messages.items():
                    logger.info(f"Received {len(records)} messages from {topic_partition}")
                    
                    for record in records:
                        try:
                            await self._process_message(record)
                        except Exception as e:
                            logger.error(f"Error processing message: {e}", exc_info=True)
                
        except Exception as e:
            logger.error(f"Kafka consumer error: {e}", exc_info=True)
        finally:
            self.stop()
    
    async def _process_message(self, record):
        """
        Process individual Kafka message
        
        Args:
            record: Kafka record
        """
        try:
            data = record.value
            logger.debug(f"Processing message: {data}")
            
            # Process through processing service
            await self.processing_service.process_iot_data(data)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            raise
    
    def stop(self):
        """Stop Kafka consumer"""
        self.running = False
        try:
            if self.consumer:
                self.consumer.close()
                logger.info("Kafka consumer stopped")
        except Exception as e:
            logger.error(f"Error stopping Kafka consumer: {e}")
