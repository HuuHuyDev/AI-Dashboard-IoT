"""
Processing Service - Business Logic
Validates, transforms, and stores IoT data with event publishing
"""
import logging
from datetime import datetime
from typing import Dict, Any

from app.repositories.log_repository import LogRepository
from app.core.redis_publisher import redis_publisher
from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


class ProcessingService:
    """Service for processing IoT data with event publishing"""
    
    def __init__(self):
        pass
    
    async def process_iot_data(self, data: Dict[str, Any]):
        """
        Process IoT data: validate, transform, store, and publish events
        
        Args:
            data: Raw IoT data from Kafka
        """
        try:
            # Step 1: Validate data
            validated_data = self._validate_data(data)
            if not validated_data:
                logger.warning(f"Invalid data: {data}")
                return
            
            # Step 2: Transform data
            transformed_data = self._transform_data(validated_data)
            
            # Step 3: Store in database with event publishing
            db = SessionLocal()
            try:
                repository = LogRepository(db)
                
                # Insert log (will also insert outbox event)
                log_id, log_data = repository.insert_log(transformed_data)
                logger.info(f"Stored log with ID: {log_id}")
                
                # Publish to Redis for real-time updates (legacy)
                await redis_publisher.publish(log_data)
                logger.debug("Published to Redis")
                
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Error processing IoT data: {e}", exc_info=True)
    
    def _validate_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate IoT data
        
        Args:
            data: Raw data
            
        Returns:
            Validated data or None if invalid
        """
        # Required fields
        required_fields = ['device_id']
        
        for field in required_fields:
            if field not in data:
                logger.error(f"Missing required field: {field}")
                return None
        
        # Validate device_id
        if not isinstance(data['device_id'], str) or not data['device_id']:
            logger.error("Invalid device_id")
            return None
        
        return data
    
    def _transform_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform and enrich IoT data
        
        Args:
            data: Validated data
            
        Returns:
            Transformed data
        """
        transformed = {
            'device_id': data['device_id'],
            'timestamp': data.get('timestamp', datetime.utcnow().isoformat()),
            'temperature': self._safe_float(data.get('temperature')),
            'humidity': self._safe_float(data.get('humidity')),
            'pressure': self._safe_float(data.get('pressure')),
            'battery_level': self._safe_float(data.get('battery_level')),
            'signal_strength': self._safe_int(data.get('signal_strength')),
            'status': data.get('status', 'normal'),
            'metadata': data.get('metadata', {})
        }
        
        # Add MQTT topic if available
        if 'mqtt_topic' in data:
            transformed['metadata']['mqtt_topic'] = data['mqtt_topic']
        
        return transformed
    
    def _safe_float(self, value) -> float:
        """Safely convert value to float"""
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None
    
    def _safe_int(self, value) -> int:
        """Safely convert value to int"""
        try:
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None
