"""
Log Repository - Database access layer for storing IoT logs
Implements Transactional Outbox Pattern for reliable event publishing
"""
import logging
from typing import Dict, Any, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime
import json
import uuid

from app.core.config import settings

logger = logging.getLogger(__name__)


class LogRepository:
    """Repository for storing IoT logs with event publishing"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def insert_log(self, data: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """
        Insert IoT log into database using Transactional Outbox Pattern
        
        Args:
            data: Log data
            
        Returns:
            Tuple of (log_id, log_data_with_id)
        """
        try:
            # Prepare SQL for log insertion
            sql = text("""
                INSERT INTO logs (
                    device_id, timestamp, temperature, humidity, pressure,
                    battery_level, signal_strength, status, metadata
                )
                VALUES (
                    :device_id, :timestamp, :temperature, :humidity, :pressure,
                    :battery_level, :signal_strength, :status, :metadata
                )
                RETURNING log_id, device_id, timestamp, temperature, humidity, 
                          pressure, battery_level, signal_strength, status, created_at
            """)
            
            # Prepare parameters
            params = {
                'device_id': data['device_id'],
                'timestamp': data.get('timestamp', datetime.utcnow()),
                'temperature': data.get('temperature'),
                'humidity': data.get('humidity'),
                'pressure': data.get('pressure'),
                'battery_level': data.get('battery_level'),
                'signal_strength': data.get('signal_strength'),
                'status': data.get('status', 'normal'),
                'metadata': json.dumps(data.get('metadata', {}))
            }
            
            # Execute query
            result = self.db.execute(sql, params)
            row = result.fetchone()
            
            # Build log data
            log_data = {
                'log_id': row[0],
                'device_id': row[1],
                'timestamp': row[2].isoformat() if row[2] else None,
                'temperature': float(row[3]) if row[3] is not None else None,
                'humidity': float(row[4]) if row[4] is not None else None,
                'pressure': float(row[5]) if row[5] is not None else None,
                'battery_level': float(row[6]) if row[6] is not None else None,
                'signal_strength': row[7],
                'status': row[8],
                'created_at': row[9].isoformat() if row[9] else None
            }
            
            # Insert event into outbox table (Transactional Outbox Pattern)
            if settings.ENABLE_EVENT_PUBLISHING:
                self._insert_outbox_event(
                    event_type='log.created',
                    aggregate_type='log',
                    aggregate_id=str(log_data['log_id']),
                    payload=log_data
                )
            
            # Commit transaction (both log and outbox event)
            self.db.commit()
            
            logger.debug(f"Inserted log with ID: {log_data['log_id']}")
            
            return log_data['log_id'], log_data
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error inserting log: {e}", exc_info=True)
            raise
    
    def insert_device(self, device_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Insert device into database with event publishing
        
        Args:
            device_data: Device data
            
        Returns:
            Inserted device data
        """
        try:
            sql = text("""
                INSERT INTO devices (
                    device_id, device_name, device_type, location, status, metadata
                )
                VALUES (
                    :device_id, :device_name, :device_type, :location, :status, :metadata
                )
                ON CONFLICT (device_id) DO UPDATE SET
                    device_name = EXCLUDED.device_name,
                    device_type = EXCLUDED.device_type,
                    location = EXCLUDED.location,
                    status = EXCLUDED.status,
                    metadata = EXCLUDED.metadata,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING device_id, device_name, device_type, location, status, created_at, updated_at
            """)
            
            params = {
                'device_id': device_data['device_id'],
                'device_name': device_data.get('device_name', 'Unknown'),
                'device_type': device_data.get('device_type', 'unknown'),
                'location': device_data.get('location'),
                'status': device_data.get('status', 'active'),
                'metadata': json.dumps(device_data.get('metadata', {}))
            }
            
            result = self.db.execute(sql, params)
            row = result.fetchone()
            
            device = {
                'device_id': row[0],
                'device_name': row[1],
                'device_type': row[2],
                'location': row[3],
                'status': row[4],
                'created_at': row[5].isoformat() if row[5] else None,
                'updated_at': row[6].isoformat() if row[6] else None
            }
            
            # Insert event into outbox
            if settings.ENABLE_EVENT_PUBLISHING:
                self._insert_outbox_event(
                    event_type='device.created',
                    aggregate_type='device',
                    aggregate_id=device['device_id'],
                    payload=device
                )
            
            self.db.commit()
            
            logger.debug(f"Inserted/Updated device: {device['device_id']}")
            
            return device
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error inserting device: {e}", exc_info=True)
            raise
    
    def _insert_outbox_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str,
        payload: Dict[str, Any]
    ):
        """
        Insert event into outbox table for reliable publishing
        
        Args:
            event_type: Type of event
            aggregate_type: Type of aggregate
            aggregate_id: ID of aggregate
            payload: Event payload
        """
        try:
            sql = text("""
                INSERT INTO outbox_events (
                    event_id, event_type, aggregate_type, aggregate_id, 
                    payload, metadata, created_at, published
                )
                VALUES (
                    :event_id, :event_type, :aggregate_type, :aggregate_id,
                    :payload, :metadata, :created_at, :published
                )
            """)
            
            event_id = str(uuid.uuid4())
            
            params = {
                'event_id': event_id,
                'event_type': event_type,
                'aggregate_type': aggregate_type,
                'aggregate_id': aggregate_id,
                'payload': json.dumps(payload, default=str),
                'metadata': json.dumps({
                    'version': '1.0',
                    'correlation_id': str(uuid.uuid4()),
                    'service': 'processing-service'
                }),
                'created_at': datetime.utcnow(),
                'published': False
            }
            
            self.db.execute(sql, params)
            logger.debug(f"Inserted outbox event: {event_type} - {event_id}")
            
        except Exception as e:
            logger.error(f"Error inserting outbox event: {e}")
            raise
    
    def get_unpublished_events(self, limit: int = 100) -> list:
        """
        Get unpublished events from outbox
        
        Args:
            limit: Maximum number of events to retrieve
            
        Returns:
            List of unpublished events
        """
        try:
            sql = text("""
                SELECT event_id, event_type, aggregate_type, aggregate_id, 
                       payload, metadata, created_at, retry_count
                FROM outbox_events
                WHERE published = FALSE
                  AND retry_count < :max_retries
                ORDER BY created_at ASC
                LIMIT :limit
            """)
            
            result = self.db.execute(sql, {
                'max_retries': settings.EVENT_RETRY_ATTEMPTS,
                'limit': limit
            })
            
            events = []
            for row in result:
                events.append({
                    'event_id': row[0],
                    'event_type': row[1],
                    'aggregate_type': row[2],
                    'aggregate_id': row[3],
                    'payload': json.loads(row[4]) if isinstance(row[4], str) else row[4],
                    'metadata': json.loads(row[5]) if isinstance(row[5], str) else row[5],
                    'created_at': row[6],
                    'retry_count': row[7]
                })
            
            return events
            
        except Exception as e:
            logger.error(f"Error getting unpublished events: {e}")
            return []
    
    def mark_event_published(self, event_id: str):
        """
        Mark event as published
        
        Args:
            event_id: Event ID
        """
        try:
            sql = text("""
                UPDATE outbox_events
                SET published = TRUE,
                    published_at = :published_at
                WHERE event_id = :event_id
            """)
            
            self.db.execute(sql, {
                'event_id': event_id,
                'published_at': datetime.utcnow()
            })
            self.db.commit()
            
            logger.debug(f"Marked event as published: {event_id}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error marking event as published: {e}")
    
    def increment_event_retry(self, event_id: str, error_message: str):
        """
        Increment retry count for failed event
        
        Args:
            event_id: Event ID
            error_message: Error message
        """
        try:
            sql = text("""
                UPDATE outbox_events
                SET retry_count = retry_count + 1,
                    last_error = :error_message
                WHERE event_id = :event_id
            """)
            
            self.db.execute(sql, {
                'event_id': event_id,
                'error_message': error_message
            })
            self.db.commit()
            
            logger.debug(f"Incremented retry count for event: {event_id}")
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error incrementing retry count: {e}")
