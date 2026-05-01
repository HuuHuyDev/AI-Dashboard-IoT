"""
Initial Data Sync Script
Syncs existing data from Processing Service to Query Service read models
Run once during migration to CQRS pattern
"""
import psycopg2
import logging
from datetime import datetime
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configurations
PROCESSING_DB_CONFIG = {
    'host': 'processing-db',
    'port': 5432,
    'database': 'processing_db',
    'user': 'processing_user',
    'password': 'processing_pass'
}

QUERY_DB_CONFIG = {
    'host': 'query-db',
    'port': 5432,
    'database': 'query_db',
    'user': 'query_user',
    'password': 'query_password'
}


def sync_devices():
    """Sync devices from Processing DB to Query DB"""
    logger.info("Syncing devices...")
    
    processing_conn = psycopg2.connect(**PROCESSING_DB_CONFIG)
    query_conn = psycopg2.connect(**QUERY_DB_CONFIG)
    
    try:
        # Read from processing_db
        with processing_conn.cursor() as cursor:
            cursor.execute("""
                SELECT device_id, device_name, device_type, location, status, created_at
                FROM devices
            """)
            devices = cursor.fetchall()
        
        # Write to query_db
        with query_conn.cursor() as cursor:
            for device in devices:
                cursor.execute("""
                    INSERT INTO device_summary (
                        device_id, device_name, device_type, location, status, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (device_id) DO UPDATE SET
                        device_name = EXCLUDED.device_name,
                        device_type = EXCLUDED.device_type,
                        location = EXCLUDED.location,
                        status = EXCLUDED.status,
                        updated_at = EXCLUDED.updated_at
                """, (
                    device[0], device[1], device[2], device[3], device[4], device[5], datetime.utcnow()
                ))
        
        query_conn.commit()
        logger.info(f"Synced {len(devices)} devices")
        
    except Exception as e:
        logger.error(f"Error syncing devices: {e}")
        query_conn.rollback()
        raise
    finally:
        processing_conn.close()
        query_conn.close()


def sync_logs(batch_size=10000):
    """Sync logs from Processing DB to Query DB"""
    logger.info("Syncing logs...")
    
    processing_conn = psycopg2.connect(**PROCESSING_DB_CONFIG)
    query_conn = psycopg2.connect(**QUERY_DB_CONFIG)
    
    try:
        # Get total count
        with processing_conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM logs")
            total_count = cursor.fetchone()[0]
        
        logger.info(f"Total logs to sync: {total_count}")
        
        # Sync in batches
        offset = 0
        while offset < total_count:
            logger.info(f"Syncing batch: {offset} - {offset + batch_size}")
            
            # Read batch from processing_db
            with processing_conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        l.log_id, l.device_id, d.device_name, d.device_type, d.location,
                        l.timestamp, l.temperature, l.humidity, l.pressure, 
                        l.battery_level, l.signal_strength, l.status, l.created_at
                    FROM logs l
                    JOIN devices d ON l.device_id = d.device_id
                    ORDER BY l.log_id
                    LIMIT %s OFFSET %s
                """, (batch_size, offset))
                logs = cursor.fetchall()
            
            if not logs:
                break
            
            # Write batch to query_db
            with query_conn.cursor() as cursor:
                for log in logs:
                    cursor.execute("""
                        INSERT INTO log_summary (
                            log_id, device_id, device_name, device_type, device_location,
                            timestamp, temperature, humidity, pressure, battery_level,
                            signal_strength, status, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (log_id) DO NOTHING
                    """, log)
            
            query_conn.commit()
            logger.info(f"Synced {len(logs)} logs")
            
            offset += batch_size
        
        logger.info(f"Total logs synced: {total_count}")
        
    except Exception as e:
        logger.error(f"Error syncing logs: {e}")
        query_conn.rollback()
        raise
    finally:
        processing_conn.close()
        query_conn.close()


def sync_daily_stats():
    """Sync daily stats from Processing DB to Query DB"""
    logger.info("Syncing daily stats...")
    
    processing_conn = psycopg2.connect(**PROCESSING_DB_CONFIG)
    query_conn = psycopg2.connect(**QUERY_DB_CONFIG)
    
    try:
        # Read from processing_db
        with processing_conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    ds.stat_id, ds.device_id, d.device_name, d.device_type, ds.date,
                    ds.avg_temperature, ds.min_temperature, ds.max_temperature,
                    ds.avg_humidity, ds.min_humidity, ds.max_humidity,
                    ds.avg_pressure, ds.min_pressure, ds.max_pressure,
                    ds.avg_battery_level, ds.record_count, ds.created_at
                FROM daily_stats ds
                JOIN devices d ON ds.device_id = d.device_id
            """)
            stats = cursor.fetchall()
        
        # Write to query_db
        with query_conn.cursor() as cursor:
            for stat in stats:
                cursor.execute("""
                    INSERT INTO daily_stats_view (
                        stat_id, device_id, device_name, device_type, date,
                        avg_temperature, min_temperature, max_temperature,
                        avg_humidity, min_humidity, max_humidity,
                        avg_pressure, min_pressure, max_pressure,
                        avg_battery_level, record_count, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                """, (*stat, datetime.utcnow()))
        
        query_conn.commit()
        logger.info(f"Synced {len(stats)} daily stats")
        
    except Exception as e:
        logger.error(f"Error syncing daily stats: {e}")
        query_conn.rollback()
        raise
    finally:
        processing_conn.close()
        query_conn.close()


def update_device_aggregates():
    """Update device summary aggregates (24h stats, latest readings)"""
    logger.info("Updating device aggregates...")
    
    query_conn = psycopg2.connect(**QUERY_DB_CONFIG)
    
    try:
        with query_conn.cursor() as cursor:
            # Update latest readings
            cursor.execute("""
                UPDATE device_summary ds
                SET 
                    last_reading_time = latest.timestamp,
                    last_temperature = latest.temperature,
                    last_humidity = latest.humidity,
                    last_pressure = latest.pressure,
                    last_battery_level = latest.battery_level,
                    total_logs_count = (
                        SELECT COUNT(*) FROM log_summary WHERE device_id = ds.device_id
                    )
                FROM (
                    SELECT DISTINCT ON (device_id)
                        device_id, timestamp, temperature, humidity, pressure, battery_level
                    FROM log_summary
                    ORDER BY device_id, timestamp DESC
                ) latest
                WHERE ds.device_id = latest.device_id
            """)
            
            # Update 24h averages
            cursor.execute("""
                UPDATE device_summary ds
                SET 
                    avg_temperature_24h = stats.avg_temperature,
                    avg_humidity_24h = stats.avg_humidity,
                    min_temperature_24h = stats.min_temperature,
                    max_temperature_24h = stats.max_temperature
                FROM (
                    SELECT 
                        device_id,
                        AVG(temperature) as avg_temperature,
                        AVG(humidity) as avg_humidity,
                        MIN(temperature) as min_temperature,
                        MAX(temperature) as max_temperature
                    FROM log_summary
                    WHERE timestamp >= NOW() - INTERVAL '24 hours'
                    GROUP BY device_id
                ) stats
                WHERE ds.device_id = stats.device_id
            """)
        
        query_conn.commit()
        logger.info("Device aggregates updated")
        
    except Exception as e:
        logger.error(f"Error updating device aggregates: {e}")
        query_conn.rollback()
        raise
    finally:
        query_conn.close()


def main():
    """Main sync function"""
    try:
        logger.info("Starting initial data sync...")
        logger.info("=" * 60)
        
        # Sync in order
        sync_devices()
        sync_logs()
        sync_daily_stats()
        update_device_aggregates()
        
        logger.info("=" * 60)
        logger.info("Initial data sync completed successfully!")
        
    except Exception as e:
        logger.error(f"Initial data sync failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
