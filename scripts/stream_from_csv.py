"""
Stream IoT data from CSV file to Kafka
Simulates real-time IoT sensor data ingestion
"""
import csv
import json
import time
import logging
from datetime import datetime
from kafka import KafkaProducer
from kafka.errors import KafkaError
import sys
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:29092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC_IOT_LOGS', 'iot_logs')
STREAM_INTERVAL = float(os.getenv('STREAM_INTERVAL', '1.0'))  # seconds


def create_producer():
    """Create Kafka producer"""
    try:
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None,
            acks='all',
            retries=3
        )
        logger.info(f"Connected to Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
        return producer
    except Exception as e:
        logger.error(f"Failed to create Kafka producer: {e}")
        sys.exit(1)


def generate_sample_data():
    """Generate sample IoT data"""
    import random
    
    devices = ['SENSOR_001', 'SENSOR_002', 'SENSOR_003', 'SENSOR_004', 'SENSOR_005']
    
    return {
        'device_id': random.choice(devices),
        'timestamp': datetime.utcnow().isoformat(),
        'temperature': round(random.uniform(18.0, 28.0), 2),
        'humidity': round(random.uniform(30.0, 70.0), 2),
        'pressure': round(random.uniform(1000.0, 1020.0), 2),
        'battery_level': round(random.uniform(70.0, 100.0), 2),
        'signal_strength': random.randint(-80, -50),
        'status': random.choice(['normal', 'normal', 'normal', 'warning'])
    }


def stream_from_csv(csv_file: str, producer: KafkaProducer):
    """
    Stream data from CSV file to Kafka
    
    Args:
        csv_file: Path to CSV file
        producer: Kafka producer instance
    """
    try:
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            
            logger.info(f"Streaming data from {csv_file}")
            logger.info(f"Sending to Kafka topic: {KAFKA_TOPIC}")
            logger.info(f"Interval: {STREAM_INTERVAL}s")
            
            count = 0
            for row in reader:
                # Convert row to proper types
                data = {
                    'device_id': row['device_id'],
                    'timestamp': row.get('timestamp', datetime.utcnow().isoformat()),
                    'temperature': float(row['temperature']) if row.get('temperature') else None,
                    'humidity': float(row['humidity']) if row.get('humidity') else None,
                    'pressure': float(row['pressure']) if row.get('pressure') else None,
                    'battery_level': float(row['battery_level']) if row.get('battery_level') else None,
                    'signal_strength': int(row['signal_strength']) if row.get('signal_strength') else None,
                    'status': row.get('status', 'normal')
                }
                
                # Send to Kafka
                producer.send(KAFKA_TOPIC, value=data, key=data['device_id'])
                count += 1
                
                if count % 10 == 0:
                    logger.info(f"Sent {count} messages")
                
                # Wait before sending next message
                time.sleep(STREAM_INTERVAL)
            
            logger.info(f"Finished streaming {count} messages from CSV")
            
    except FileNotFoundError:
        logger.error(f"CSV file not found: {csv_file}")
    except Exception as e:
        logger.error(f"Error streaming from CSV: {e}", exc_info=True)


def stream_generated_data(producer: KafkaProducer, duration: int = None):
    """
    Stream randomly generated data to Kafka
    
    Args:
        producer: Kafka producer instance
        duration: Duration in seconds (None for infinite)
    """
    logger.info("Streaming generated IoT data")
    logger.info(f"Sending to Kafka topic: {KAFKA_TOPIC}")
    logger.info(f"Interval: {STREAM_INTERVAL}s")
    
    count = 0
    start_time = time.time()
    
    try:
        while True:
            # Check duration
            if duration and (time.time() - start_time) > duration:
                break
            
            # Generate and send data
            data = generate_sample_data()
            producer.send(KAFKA_TOPIC, value=data, key=data['device_id'])
            count += 1
            
            if count % 10 == 0:
                logger.info(f"Sent {count} messages")
            
            # Wait before sending next message
            time.sleep(STREAM_INTERVAL)
            
    except KeyboardInterrupt:
        logger.info("Streaming interrupted by user")
    finally:
        logger.info(f"Finished streaming {count} messages")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Stream IoT data to Kafka')
    parser.add_argument('--csv', type=str, help='Path to CSV file')
    parser.add_argument('--duration', type=int, help='Duration in seconds (for generated data)')
    parser.add_argument('--generate', action='store_true', help='Generate random data instead of CSV')
    
    args = parser.parse_args()
    
    # Create Kafka producer
    producer = create_producer()
    
    try:
        if args.csv:
            # Stream from CSV
            stream_from_csv(args.csv, producer)
        else:
            # Stream generated data
            stream_generated_data(producer, args.duration)
    finally:
        # Close producer
        producer.flush()
        producer.close()
        logger.info("Kafka producer closed")


if __name__ == "__main__":
    main()
