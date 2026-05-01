"""
Kafka Producer - Sends IoT data to Kafka topic
"""
from kafka import KafkaProducer
from kafka.errors import KafkaError
import logging
import json
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class KafkaProducerClient:
    """Kafka producer for sending IoT data"""
    
    def __init__(self):
        self.producer: Optional[KafkaProducer] = None
        self.topic = settings.KAFKA_TOPIC_IOT_LOGS
        self._connect()
    
    def _connect(self):
        """Establish Kafka producer connection"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas
                retries=3,
                max_in_flight_requests_per_connection=1,
                compression_type='gzip'
            )
            logger.info(f"Kafka producer connected to {settings.KAFKA_BOOTSTRAP_SERVERS}")
        except Exception as e:
            logger.error(f"Failed to connect Kafka producer: {e}")
            raise
    
    def send_message(self, data: dict, key: Optional[str] = None):
        """
        Send message to Kafka topic
        
        Args:
            data: Message data
            key: Optional message key (for partitioning)
        """
        if not self.producer:
            logger.error("Kafka producer not initialized")
            return
        
        try:
            # Use device_id as key for partitioning
            if not key and 'device_id' in data:
                key = data['device_id']
            
            # Send message
            future = self.producer.send(
                self.topic,
                value=data,
                key=key
            )
            
            # Add callback
            future.add_callback(self._on_send_success)
            future.add_errback(self._on_send_error)
            
        except Exception as e:
            logger.error(f"Error sending message to Kafka: {e}")
    
    def _on_send_success(self, record_metadata):
        """Callback on successful send"""
        logger.debug(
            f"Message sent to {record_metadata.topic} "
            f"partition {record_metadata.partition} "
            f"offset {record_metadata.offset}"
        )
    
    def _on_send_error(self, exc):
        """Callback on send error"""
        logger.error(f"Error sending message to Kafka: {exc}")
    
    def close(self):
        """Close Kafka producer"""
        try:
            if self.producer:
                self.producer.flush()
                self.producer.close()
                logger.info("Kafka producer closed")
        except Exception as e:
            logger.error(f"Error closing Kafka producer: {e}")
