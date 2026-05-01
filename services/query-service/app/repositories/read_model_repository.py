"""
Read Model Repository - Database operations for read models
Implements CQRS pattern with denormalized tables
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class ReadModelRepository:
    """Repository for read model operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def is_event_processed(self, event_id: str) -> bool:
        """
        Check if event has already been processed (idempotency)
        
        Args:
            event_id: Event ID
            
        Returns:
            True if already processed
        """
        try:
            result = self.db.execute(
                text("SELECT 1 FROM processed_events WHERE event_id = :event_id"),
                {"event_id": event_id}
            )
            return result.fetchone() is not None
        except Exception as e:
            logger.error(f"Error checking event processed: {e}")
            return False
    
    def create_device_summary(self, data: Dict[str, Any]):
        """
        Create device summary from device.created event
        
        Args:
            data: Device data
        """
        try:
            self.db.execute(
                text("""
                    INSERT INTO device_summary (
                        device_id, device_name, device_type, location, status, created_at, updated_at
                    ) VALUES (
                        :device_id, :device_name, :device_type, :location, :status, :created_at, :updated_at
                    )
                    ON CONFLICT (device_id) DO NOTHING
                """),
                {
                    "device_id": data.get("device_id"),
                    "device_name": data.get("device_name"),
                    "device_type": data.get("device_type"),
                    "location": data.get("location"),
                    "status": data.get("status", "active"),
                    "created_at": data.get("created_at", datetime.utcnow()),
                    "updated_at": datetime.utcnow()
                }
            )
            logger.info(f"Created device summary: {data.get('device_id')}")
        except Exception as e:
            logger.error(f"Error creating device summary: {e}")
            raise
    
    def update_device_summary(self, data: Dict[str, Any]):
        """
        Update device summary from device.updated event
        
        Args:
            data: Device data
        """
        try:
            self.db.execute(
                text("""
                    UPDATE device_summary
                    SET device_name = :device_name,
                        device_type = :device_type,
                        location = :location,
                        status = :status,
                        updated_at = :updated_at
                    WHERE device_id = :device_id
                """),
                {
                    "device_id": data.get("device_id"),
                    "device_name": data.get("device_name"),
                    "device_type": data.get("device_type"),
                    "location": data.get("location"),
                    "status": data.get("status"),
                    "updated_at": datetime.utcnow()
                }
            )
            logger.info(f"Updated device summary: {data.get('device_id')}")
        except Exception as e:
            logger.error(f"Error updating device summary: {e}")
            raise
    
    def create_log_summary(self, data: Dict[str, Any]):
        """
        Create log summary from log.created event
        
        Args:
            data: Log data
        """
        try:
            # Get device info for denormalization
            device_info = self.db.execute(
                text("SELECT device_name, device_type, location FROM device_summary WHERE device_id = :device_id"),
                {"device_id": data.get("device_id")}
            ).fetchone()
            
            self.db.execute(
                text("""
                    INSERT INTO log_summary (
                        log_id, device_id, device_name, device_type, device_location,
                        timestamp, temperature, humidity, pressure, battery_level,
                        signal_strength, status, created_at
                    ) VALUES (
                        :log_id, :device_id, :device_name, :device_type, :device_location,
                        :timestamp, :temperature, :humidity, :pressure, :battery_level,
                        :signal_strength, :status, :created_at
                    )
                    ON CONFLICT (log_id) DO NOTHING
                """),
                {
                    "log_id": data.get("log_id"),
                    "device_id": data.get("device_id"),
                    "device_name": device_info[0] if device_info else None,
                    "device_type": device_info[1] if device_info else None,
                    "device_location": device_info[2] if device_info else None,
                    "timestamp": data.get("timestamp"),
                    "temperature": data.get("temperature"),
                    "humidity": data.get("humidity"),
                    "pressure": data.get("pressure"),
                    "battery_level": data.get("battery_level"),
                    "signal_strength": data.get("signal_strength"),
                    "status": data.get("status", "normal"),
                    "created_at": datetime.utcnow()
                }
            )
            logger.info(f"Created log summary: {data.get('log_id')}")
        except Exception as e:
            logger.error(f"Error creating log summary: {e}")
            raise
    
    def update_device_latest_reading(self, data: Dict[str, Any]):
        """
        Update device summary with latest reading from log
        
        Args:
            data: Log data
        """
        try:
            self.db.execute(
                text("""
                    UPDATE device_summary
                    SET last_reading_time = :timestamp,
                        last_temperature = :temperature,
                        last_humidity = :humidity,
                        last_pressure = :pressure,
                        last_battery_level = :battery_level,
                        total_logs_count = total_logs_count + 1,
                        updated_at = :updated_at
                    WHERE device_id = :device_id
                """),
                {
                    "device_id": data.get("device_id"),
                    "timestamp": data.get("timestamp"),
                    "temperature": data.get("temperature"),
                    "humidity": data.get("humidity"),
                    "pressure": data.get("pressure"),
                    "battery_level": data.get("battery_level"),
                    "updated_at": datetime.utcnow()
                }
            )
            logger.debug(f"Updated device latest reading: {data.get('device_id')}")
        except Exception as e:
            logger.error(f"Error updating device latest reading: {e}")
            raise
    
    def update_device_24h_stats(self, device_id: str):
        """
        Update device 24h average statistics
        
        Args:
            device_id: Device ID
        """
        try:
            # Calculate 24h averages from log_summary
            stats = self.db.execute(
                text("""
                    SELECT 
                        AVG(temperature) as avg_temperature,
                        AVG(humidity) as avg_humidity,
                        MIN(temperature) as min_temperature,
                        MAX(temperature) as max_temperature
                    FROM log_summary
                    WHERE device_id = :device_id
                    AND timestamp >= :time_24h_ago
                """),
                {
                    "device_id": device_id,
                    "time_24h_ago": datetime.utcnow() - timedelta(hours=24)
                }
            ).fetchone()
            
            if stats:
                self.db.execute(
                    text("""
                        UPDATE device_summary
                        SET avg_temperature_24h = :avg_temperature,
                            avg_humidity_24h = :avg_humidity,
                            min_temperature_24h = :min_temperature,
                            max_temperature_24h = :max_temperature,
                            updated_at = :updated_at
                        WHERE device_id = :device_id
                    """),
                    {
                        "device_id": device_id,
                        "avg_temperature": stats[0],
                        "avg_humidity": stats[1],
                        "min_temperature": stats[2],
                        "max_temperature": stats[3],
                        "updated_at": datetime.utcnow()
                    }
                )
                logger.debug(f"Updated device 24h stats: {device_id}")
        except Exception as e:
            logger.error(f"Error updating device 24h stats: {e}")
            raise
    
    def upsert_daily_stats_view(self, data: Dict[str, Any]):
        """
        Upsert daily stats view from stats.updated event
        
        Args:
            data: Stats data
        """
        try:
            # Get device info for denormalization
            device_info = self.db.execute(
                text("SELECT device_name, device_type FROM device_summary WHERE device_id = :device_id"),
                {"device_id": data.get("device_id")}
            ).fetchone()
            
            self.db.execute(
                text("""
                    INSERT INTO daily_stats_view (
                        stat_id, device_id, device_name, device_type, date,
                        avg_temperature, min_temperature, max_temperature,
                        avg_humidity, min_humidity, max_humidity,
                        avg_pressure, min_pressure, max_pressure,
                        avg_battery_level, record_count, created_at, updated_at
                    ) VALUES (
                        :stat_id, :device_id, :device_name, :device_type, :date,
                        :avg_temperature, :min_temperature, :max_temperature,
                        :avg_humidity, :min_humidity, :max_humidity,
                        :avg_pressure, :min_pressure, :max_pressure,
                        :avg_battery_level, :record_count, :created_at, :updated_at
                    )
                    ON CONFLICT (device_id, date) DO UPDATE SET
                        avg_temperature = EXCLUDED.avg_temperature,
                        min_temperature = EXCLUDED.min_temperature,
                        max_temperature = EXCLUDED.max_temperature,
                        avg_humidity = EXCLUDED.avg_humidity,
                        min_humidity = EXCLUDED.min_humidity,
                        max_humidity = EXCLUDED.max_humidity,
                        avg_pressure = EXCLUDED.avg_pressure,
                        min_pressure = EXCLUDED.min_pressure,
                        max_pressure = EXCLUDED.max_pressure,
                        avg_battery_level = EXCLUDED.avg_battery_level,
                        record_count = EXCLUDED.record_count,
                        updated_at = EXCLUDED.updated_at
                """),
                {
                    "stat_id": data.get("stat_id"),
                    "device_id": data.get("device_id"),
                    "device_name": device_info[0] if device_info else None,
                    "device_type": device_info[1] if device_info else None,
                    "date": data.get("date"),
                    "avg_temperature": data.get("avg_temperature"),
                    "min_temperature": data.get("min_temperature"),
                    "max_temperature": data.get("max_temperature"),
                    "avg_humidity": data.get("avg_humidity"),
                    "min_humidity": data.get("min_humidity"),
                    "max_humidity": data.get("max_humidity"),
                    "avg_pressure": data.get("avg_pressure"),
                    "min_pressure": data.get("min_pressure"),
                    "max_pressure": data.get("max_pressure"),
                    "avg_battery_level": data.get("avg_battery_level"),
                    "record_count": data.get("record_count"),
                    "created_at": data.get("created_at", datetime.utcnow()),
                    "updated_at": datetime.utcnow()
                }
            )
            logger.info(f"Upserted daily stats view: {data.get('stat_id')}")
        except Exception as e:
            logger.error(f"Error upserting daily stats view: {e}")
            raise
    
    def mark_event_processed(self, event_id: str, event_type: str, aggregate_id: str, processing_time_ms: int):
        """
        Mark event as processed (idempotency)
        
        Args:
            event_id: Event ID
            event_type: Event type
            aggregate_id: Aggregate ID
            processing_time_ms: Processing time in milliseconds
        """
        try:
            self.db.execute(
                text("""
                    INSERT INTO processed_events (
                        event_id, event_type, aggregate_id, processed_at, processing_time_ms
                    ) VALUES (
                        :event_id, :event_type, :aggregate_id, :processed_at, :processing_time_ms
                    )
                    ON CONFLICT (event_id) DO NOTHING
                """),
                {
                    "event_id": event_id,
                    "event_type": event_type,
                    "aggregate_id": aggregate_id,
                    "processed_at": datetime.utcnow(),
                    "processing_time_ms": processing_time_ms
                }
            )
            logger.debug(f"Marked event processed: {event_id}")
        except Exception as e:
            logger.error(f"Error marking event processed: {e}")
            raise
