"""
Event Publisher - Publishes domain events to Kafka
Implements event-driven architecture for microservices communication
"""
from kafka import KafkaProducer
from kafka.errors import KafkaError
import logging
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)


class EventPublisher:
    """Kafka event publisher for domain events"""
    
    def __init__(self):
        self.producer: Optional[KafkaProducer] = None
        self.topic_prefix = settings.KAFKA_EVENT_TOPIC_PREFIX
        self._connect()
    
    def _connect(self):
        """Establish Kafka producer connection"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',  # Wait for all replicas
                retries=3,
                max_in_flight_requests_per_connection=1,
                compression_type='gzip',
                request_timeout_ms=30000,
                retry_backoff_ms=100
            )
            logger.info(f"Event publisher connected to {settings.KAFKA_BOOTSTRAP_SERVERS}")
        except Exception as e:
            logger.error(f"Failed to connect event publisher: {e}")
            raise
    
    def publish_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> bool:
        """
        Publish domain event to Kafka
        
        Args:
            event_type: Type of event (e.g., 'device.created', 'log.created')
            aggregate_type: Type of aggregate (e.g., 'device', 'log')
            aggregate_id: ID of the aggregate
            data: Event payload data
            correlation_id: Optional correlation ID for tracing
            
        Returns:
            Success status
        """
        if not self.producer:
            logger.error("Event publisher not initialized")
            return False
        
        try:
            # Build event envelope
            event = self._build_event_envelope(
                event_type=event_type,
                aggregate_type=aggregate_type,
                aggregate_id=aggregate_id,
                data=data,
                correlation_id=correlation_id
            )
            
            # Determine topic
            topic = self._get_topic_name(event_type)
            
            # Publish to Kafka
            future = self.producer.send(
                topic,
                value=event,
                key=aggregate_id
            )
            
            # Add callbacks
            future.add_callback(self._on_send_success, event_type, aggregate_id)
            future.add_errback(self._on_send_error, event_type, aggregate_id)
            
            # Flush to ensure delivery
            self.producer.flush(timeout=5)
            
            logger.info(f"Published event: {event_type} for {aggregate_type}:{aggregate_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error publishing event {event_type}: {e}", exc_info=True)
            return False
    
    def _build_event_envelope(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        data: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Build event envelope with metadata
        
        Args:
            event_type: Type of event
            aggregate_type: Type of aggregate
            aggregate_id: ID of the aggregate
            data: Event payload
            correlation_id: Optional correlation ID
            
        Returns:
            Event envelope
        """
        return {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "timestamp": datetime.utcnow().isoformat(),
            "service": "processing-service",
            "data": data,
            "metadata": {
                "version": "1.0",
                "correlation_id": correlation_id or str(uuid.uuid4()),
                "schema_version": "1.0.0"
            }
        }
    
    def _get_topic_name(self, event_type: str) -> str:
        """
        Get Kafka topic name for event type
        
        Args:
            event_type: Event type (e.g., 'device.created')
            
        Returns:
            Full topic name
        """
        return f"{self.topic_prefix}{event_type}"
    
    def _on_send_success(self, record_metadata, event_type: str, aggregate_id: str):
        """Callback on successful send"""
        logger.debug(
            f"Event {event_type} for {aggregate_id} sent to "
            f"{record_metadata.topic} partition {record_metadata.partition} "
            f"offset {record_metadata.offset}"
        )
    
    def _on_send_error(self, exc, event_type: str, aggregate_id: str):
        """Callback on send error"""
        logger.error(f"Error sending event {event_type} for {aggregate_id}: {exc}")
    
    def publish_device_created(self, device_data: Dict[str, Any]) -> bool:
        """Publish device.created event"""
        return self.publish_event(
            event_type="device.created",
            aggregate_type="device",
            aggregate_id=device_data.get("device_id"),
            data=device_data
        )
    
    def publish_device_updated(self, device_data: Dict[str, Any]) -> bool:
        """Publish device.updated event"""
        return self.publish_event(
            event_type="device.updated",
            aggregate_type="device",
            aggregate_id=device_data.get("device_id"),
            data=device_data
        )
    
    def publish_log_created(self, log_data: Dict[str, Any]) -> bool:
        """Publish log.created event"""
        return self.publish_event(
            event_type="log.created",
            aggregate_type="log",
            aggregate_id=str(log_data.get("log_id")),
            data=log_data
        )
    
    def publish_stats_updated(self, stats_data: Dict[str, Any]) -> bool:
        """Publish stats.updated event"""
        return self.publish_event(
            event_type="stats.updated",
            aggregate_type="daily_stats",
            aggregate_id=str(stats_data.get("stat_id")),
            data=stats_data
        )
    
    def publish_alert_created(self, alert_data: Dict[str, Any]) -> bool:
        """Publish alert.created event"""
        return self.publish_event(
            event_type="alert.created",
            aggregate_type="alert",
            aggregate_id=str(alert_data.get("alert_id")),
            data=alert_data
        )
    
    def close(self):
        """Close Kafka producer"""
        try:
            if self.producer:
                self.producer.flush()
                self.producer.close()
                logger.info("Event publisher closed")
        except Exception as e:
            logger.error(f"Error closing event publisher: {e}")


# Global event publisher instance
event_publisher = EventPublisher()
