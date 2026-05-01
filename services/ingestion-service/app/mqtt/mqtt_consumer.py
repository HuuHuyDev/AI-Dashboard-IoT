"""
MQTT Consumer - Receives IoT data from MQTT broker
"""
import paho.mqtt.client as mqtt
import logging
import json
import time
import asyncio
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class MQTTConsumer:
    """MQTT consumer for receiving IoT sensor data"""
    
    def __init__(self, kafka_producer, metrics_service=None, rate_limiter=None, retry_service=None):
        self.kafka_producer = kafka_producer
        self.metrics_service = metrics_service
        self.rate_limiter = rate_limiter
        self.retry_service = retry_service
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        self._setup_client()
    
    def _setup_client(self):
        """Setup MQTT client with callbacks"""
        self.client = mqtt.Client(client_id=settings.MQTT_CLIENT_ID)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            self.connected = True
            logger.info("Connected to MQTT broker")
            
            # Subscribe to topic
            client.subscribe(settings.MQTT_TOPIC)
            logger.info(f"Subscribed to topic: {settings.MQTT_TOPIC}")
        else:
            logger.error(f"Failed to connect to MQTT broker: {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected disconnection from MQTT broker: {rc}")
        else:
            logger.info("Disconnected from MQTT broker")
    
    def _on_message(self, client, userdata, msg):
        """
        Callback when message received from MQTT
        
        Args:
            client: MQTT client
            userdata: User data
            msg: MQTT message
        """
        start_time = time.time()
        
        try:
            # Parse message
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            logger.debug(f"Received message from {topic}: {payload[:100]}")
            
            # Validate JSON
            try:
                data = json.loads(payload)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in message: {payload}")
                return
            
            device_id = data.get('device_id', 'unknown')
            
            # Track metrics
            if self.metrics_service:
                asyncio.run(self.metrics_service.increment_received(device_id))
            
            # Check rate limits
            if self.rate_limiter:
                if not asyncio.run(self.rate_limiter.check_device_limit(device_id)):
                    logger.warning(f"Rate limit exceeded for device: {device_id}")
                    return
                
                if not asyncio.run(self.rate_limiter.check_global_limit()):
                    logger.warning("Global rate limit exceeded")
                    return
            
            # Add metadata
            data['mqtt_topic'] = topic
            
            # Forward to Kafka
            try:
                self.kafka_producer.send_message(data)
                if self.metrics_service:
                    asyncio.run(self.metrics_service.increment_sent(device_id))
            except Exception as e:
                logger.error(f"Failed to send to Kafka: {e}")
                if self.metrics_service:
                    asyncio.run(self.metrics_service.increment_failed(device_id))
                if self.retry_service:
                    asyncio.run(self.retry_service.add_failed_message(data, str(e)))
            
            # Record processing time
            if self.metrics_service:
                duration_ms = (time.time() - start_time) * 1000
                asyncio.run(self.metrics_service.record_processing_time(duration_ms))
            
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}", exc_info=True)
    
    def start(self):
        """Start MQTT consumer"""
        try:
            logger.info(f"Connecting to MQTT broker at {settings.MQTT_BROKER}:{settings.MQTT_PORT}")
            self.client.connect(
                settings.MQTT_BROKER,
                settings.MQTT_PORT,
                settings.MQTT_KEEPALIVE
            )
            
            # Start network loop in background thread
            self.client.loop_start()
            logger.info("MQTT consumer started")
            
        except Exception as e:
            logger.error(f"Failed to start MQTT consumer: {e}")
            raise
    
    def stop(self):
        """Stop MQTT consumer"""
        try:
            if self.client:
                self.client.loop_stop()
                self.client.disconnect()
                logger.info("MQTT consumer stopped")
        except Exception as e:
            logger.error(f"Error stopping MQTT consumer: {e}")
