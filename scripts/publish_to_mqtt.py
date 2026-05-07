#!/usr/bin/env python3
"""
Script Publish Dữ Liệu Từ CSV Qua MQTT
Tối ưu cho xử lý file lớn với chunking và checkpoint
"""
import os
import json
import logging
import time
import hashlib
import pickle
from pathlib import Path
from typing import Optional, List, Dict, Iterator
import argparse
from datetime import datetime
import pandas as pd
import paho.mqtt.client as mqtt
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MQTTPublisher:
    """Publish dữ liệu qua MQTT với batch optimization"""

    def __init__(self, broker: str = "localhost", port: int = 1883, batch_size: int = 200):
        self.broker = broker
        self.port = port
        self.batch_size = batch_size
        self.client = None
        self.connected = False
        self.published_count = 0
        self.failed_count = 0
        self._setup_client()

    def _setup_client(self):
        """Setup MQTT client"""
        self.client = mqtt.Client(client_id=f"bulk_publisher_{datetime.now().timestamp()}")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_publish = self._on_publish

        logger.info(f"Connecting to MQTT broker at {self.broker}:{self.port}")
        self.client.connect(self.broker, self.port, keepalive=60)
        self.client.loop_start()

        # Wait for connection
        timeout = 10
        start = time.time()
        while not self.connected and (time.time() - start) < timeout:
            time.sleep(0.1)

        if not self.connected:
            raise ConnectionError(f"Failed to connect to MQTT broker within {timeout}s")

        logger.info("✓ Connected to MQTT broker")

    def _on_connect(self, client, userdata, flags, rc):
        """MQTT connect callback"""
        if rc == 0:
            self.connected = True
            logger.info("✓ MQTT Connected")
        else:
            logger.error(f"MQTT Connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """MQTT disconnect callback"""
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection: {rc}")

    def _on_publish(self, client, userdata, mid):
        """MQTT publish callback"""
        pass  # Silent success

    def publish_batch(self, messages: List[Dict], topic_template: str = "iot/sensors/{device_id}"):
        """
        Publish batch của messages

        Args:
            messages: List of message dicts
            topic_template: Template for topic (e.g., "iot/sensors/{device_id}")
        """
        for msg in messages:
            topic = topic_template.format(device_id=msg.get("device_id", "unknown"))

            try:
                self.client.publish(topic, json.dumps(msg), qos=1)
                self.published_count += 1
            except Exception as e:
                logger.error(f"Failed to publish: {e}")
                self.failed_count += 1

    def close(self):
        """Close MQTT connection"""
        try:
            self.client.loop_stop()
            self.client.disconnect()
            logger.info("✓ MQTT connection closed")
        except Exception as e:
            logger.error(f"Error closing MQTT: {e}")


class DataReader:
    """Read data từ CSV/Parquet files với chunking"""

    def __init__(self, file_path: Path, chunk_size: int = 5000):
        self.file_path = Path(file_path)
        self.chunk_size = chunk_size
        self.total_rows = None
        self._detect_file_type()

    def _detect_file_type(self):
        """Detect file type"""
        self.file_type = self.file_path.suffix.lower()
        if self.file_type not in ['.csv', '.parquet', '.pq']:
            raise ValueError(f"Unsupported file type: {self.file_type}")

    def _get_total_rows(self) -> int:
        """Estimate total rows"""
        if self.file_type == '.csv':
            # Quick estimate by reading first and last chunk
            df = pd.read_csv(self.file_path, nrows=100)
            return int(self.file_path.stat().st_size / (df.memory_usage(deep=True).sum() / len(df)))
        else:
            df = pd.read_parquet(self.file_path, columns=[df.columns[0]])
            return len(df)

    def read_chunks(self) -> Iterator[pd.DataFrame]:
        """Read file in chunks"""
        if self.file_type == '.csv':
            chunks = pd.read_csv(self.file_path, chunksize=self.chunk_size)
        else:
            chunks = pd.read_parquet(self.file_path)
            # For parquet, yield manual chunks
            for i in range(0, len(chunks), self.chunk_size):
                yield chunks.iloc[i:i+self.chunk_size]
            return

        for chunk in chunks:
            yield chunk


class DataTransformer:
    """Transform data để match IoT schema"""

    @staticmethod
    def transform_row(row: pd.Series, timestamp_col: Optional[str] = None) -> Dict:
        """
        Transform pandas row to IoT message

        Args:
            row: Pandas series
            timestamp_col: Name of timestamp column (auto-detect if None)

        Returns:
            Dict suitable for MQTT/Kafka
        """
        msg = {}

        # Auto-detect device_id column
        for col in ['device_id', 'device', 'sensor_id', 'id']:
            if col in row.index:
                msg['device_id'] = str(row[col])
                break

        if 'device_id' not in msg:
            msg['device_id'] = f"device_{hash(str(row)) % 10000}"

        # Auto-detect timestamp
        if timestamp_col and timestamp_col in row.index:
            msg['timestamp'] = str(row[timestamp_col])
        else:
            # Find timestamp column
            for col in row.index:
                if 'time' in col.lower() or 'date' in col.lower():
                    msg['timestamp'] = str(row[col])
                    break
            else:
                msg['timestamp'] = datetime.now().isoformat()

        # Add all numeric/string columns as metrics
        for col, val in row.items():
            if col not in ["device_id", "timestamp"]:
                if pd.notna(val):
                    try:
                        # Try to convert to number
                        msg[col] = float(val)
                    except (ValueError, TypeError):
                        msg[col] = str(val)

        return msg

    @staticmethod
    def transform_chunk(df: pd.DataFrame, timestamp_col: Optional[str] = None) -> List[Dict]:
        """Transform DataFrame chunk to messages"""
        messages = []
        for _, row in df.iterrows():
            try:
                msg = DataTransformer.transform_row(row, timestamp_col)
                messages.append(msg)
            except Exception as e:
                logger.warning(f"Failed to transform row: {e}")
        return messages


class CheckpointManager:
    """Manage progress checkpoints"""

    def __init__(self, checkpoint_dir: str = ".checkpoints"):
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(exist_ok=True)

    def get_checkpoint_file(self, source_file: Path) -> Path:
        """Get checkpoint file for source"""
        file_hash = hashlib.md5(str(source_file).encode()).hexdigest()
        return self.checkpoint_dir / f"checkpoint_{file_hash}.pkl"

    def save_checkpoint(self, source_file: Path, row_number: int, timestamp: str):
        """Save progress checkpoint"""
        checkpoint_file = self.get_checkpoint_file(source_file)
        data = {"row_number": row_number, "timestamp": timestamp, "source_file": str(source_file)}

        try:
            with open(checkpoint_file, "wb") as f:
                pickle.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    def load_checkpoint(self, source_file: Path) -> Optional[Dict]:
        """Load progress checkpoint"""
        checkpoint_file = self.get_checkpoint_file(source_file)

        if not checkpoint_file.exists():
            return None

        try:
            with open(checkpoint_file, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None


def main():
    parser = argparse.ArgumentParser(description="Publish IoT data to MQTT")
    parser.add_argument("--file", required=True, help="CSV or Parquet file path")
    parser.add_argument("--broker", default="localhost", help="MQTT broker address")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--batch", type=int, default=200, help="Batch size")
    parser.add_argument("--timestamp-col", help="Name of timestamp column")
    parser.add_argument("--resume", action="store_true", default=True, help="Resume from checkpoint")

    args = parser.parse_args()

    # Validate file exists
    file_path = Path(args.file)
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        return

    # Initialize publisher
    publisher = MQTTPublisher(args.broker, args.port, args.batch)

    try:
        # Load checkpoint
        checkpoint_manager = CheckpointManager()
        checkpoint = None
        if args.resume:
            checkpoint = checkpoint_manager.load_checkpoint(file_path)

        start_row = checkpoint["row_number"] if checkpoint else 0
        if checkpoint:
            logger.info(f"📋 Resuming from row {start_row} (timestamp: {checkpoint['timestamp']})")

        # Read file
        reader = DataReader(file_path, chunk_size=args.batch)

        # Progress bar
        total_rows = reader._get_total_rows()
        pbar = tqdm(total=total_rows, initial=start_row, desc="Publishing")

        try:
            total_published = 0
            total_failed = 0

            for chunk_idx, chunk in enumerate(reader.read_chunks()):
                # Skip if resuming
                if checkpoint and chunk_idx * args.batch < start_row:
                    continue

                # Transform
                messages = DataTransformer.transform_chunk(chunk, args.timestamp_col)

                # Publish batch
                try:
                    publisher.publish_batch(messages)
                    total_published += len(messages)

                    # Save checkpoint every 10 batches
                    if (chunk_idx + 1) % 10 == 0:
                        last_ts = messages[-1].get("timestamp", datetime.now().isoformat())
                        checkpoint_manager.save_checkpoint(
                            file_path,
                            start_row + total_published,
                            last_ts
                        )

                    # Update progress
                    pbar.update(len(messages))
                    pbar.set_postfix({
                        "published": publisher.published_count,
                        "failed": publisher.failed_count
                    })

                except Exception as e:
                    logger.error(f"Failed to publish batch {chunk_idx}: {e}")
                    total_failed += len(messages)

        finally:
            pbar.close()

        # Summary
        logger.info("✅ Publishing complete!")
        logger.info(f"  Total published: {publisher.published_count}")
        logger.info(f"  Failed: {publisher.failed_count}")
        logger.info(".2f")

    finally:
        publisher.close()


if __name__ == "__main__":
    main()