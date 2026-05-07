#!/usr/bin/env python3
"""
Script Tải 10GB Dữ Liệu IoT Từ Nhiều Nguồn
Hỗ trợ Kaggle, Google Drive, và direct downloads
"""
import os
import requests
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Optional
import argparse
import time
import logging
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class IoTDataDownloader:
    """Download IoT datasets từ nhiều nguồn"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Các datasets IoT lớn (>1GB) uy tín
        self.datasets = {
            "kaggle": [
                {
                    "name": "smart-home-dataset-with-weather-information",
                    "url": "kaggle datasets download -d seattlewebsmart/home-electricity-dataset",
                    "size": "~2GB",
                    "description": "Smart home electricity data với weather info"
                },
                {
                    "name": "iot-network-intrusion-dataset",
                    "url": "kaggle datasets download -d somertonman/iot-network-intrusion-dataset",
                    "size": "~1.5GB",
                    "description": "IoT network intrusion detection data"
                },
                {
                    "name": "environmental-sensor-data",
                    "url": "kaggle datasets download -d garystafford/environmental-sensor-data-132k",
                    "size": "~500MB",
                    "description": "Environmental sensor readings"
                },
                {
                    "name": "iot-devices-captures",
                    "url": "kaggle datasets download -d gianmarcoguaitoli/83-iot-devices-captures",
                    "size": "~1GB",
                    "description": "83 IoT devices network captures"
                }
            ],
            "direct": [
                {
                    "name": "uci-har-dataset",
                    "url": "https://archive.ics.uci.edu/ml/machine-learning-databases/00341/HAPT%20Data%20Set.zip",
                    "size": "~500MB",
                    "description": "Human Activity Recognition from smartphones"
                },
                {
                    "name": "wisdm-dataset",
                    "url": "https://www.cis.fordham.edu/wisdm/includes/datasets/latest/WISDM_ar_v1.1_raw.txt.gz",
                    "size": "~100MB",
                    "description": "Wireless Sensor Data Mining smartphone data"
                }
            ],
            "generated": [
                {
                    "name": "synthetic-iot-data",
                    "size": "10GB+",
                    "description": "Generate synthetic IoT data locally"
                }
            ]
        }

    def setup_kaggle_auth(self):
        """Setup Kaggle authentication"""
        logger.info("🔐 Setting up Kaggle authentication...")

        try:
            # Check if already authenticated
            result = subprocess.run([sys.executable, '-m', 'kaggle', 'competitions', 'list'],
                                  capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                logger.info("✓ Kaggle already authenticated")
                return True
            else:
                logger.info("❌ Kaggle authentication required")
                logger.info("Please run: kaggle auth login")
                logger.info("Or download kaggle.json from https://www.kaggle.com/account")
                logger.info("And place it in ~/.kaggle/kaggle.json")
                return False

        except Exception as e:
            logger.error(f"Error checking Kaggle auth: {e}")
            return False

    def download_kaggle_dataset(self, dataset_info: Dict) -> bool:
        """Download dataset từ Kaggle"""
        dataset_name = dataset_info['name']
        download_cmd = dataset_info['url']

        logger.info(f"📥 Downloading {dataset_name} from Kaggle...")
        logger.info(f"   Size: {dataset_info['size']}")
        logger.info(f"   Description: {dataset_info['description']}")

        try:
            # Run kaggle download command
            cmd = download_cmd.split()
            result = subprocess.run([sys.executable, '-m'] + cmd,
                                  cwd=self.data_dir,
                                  capture_output=True,
                                  text=True,
                                  timeout=3600)  # 1 hour timeout

            if result.returncode == 0:
                logger.info(f"✓ Downloaded {dataset_name}")

                # Extract if it's a zip file
                zip_files = list(self.data_dir.glob("*.zip"))
                if zip_files:
                    for zip_file in zip_files:
                        logger.info(f"📦 Extracting {zip_file.name}...")
                        subprocess.run(['powershell', 'Expand-Archive', str(zip_file), str(self.data_dir)],
                                     check=True)
                        zip_file.unlink()  # Remove zip after extraction

                return True
            else:
                logger.error(f"❌ Failed to download {dataset_name}")
                logger.error(f"Error: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"❌ Download timeout for {dataset_name}")
            return False
        except Exception as e:
            logger.error(f"❌ Error downloading {dataset_name}: {e}")
            return False

    def download_direct_file(self, dataset_info: Dict) -> bool:
        """Download file trực tiếp từ URL"""
        url = dataset_info['url']
        filename = url.split('/')[-1]
        filepath = self.data_dir / filename

        logger.info(f"📥 Downloading {dataset_info['name']}...")
        logger.info(f"   URL: {url}")
        logger.info(f"   Size: {dataset_info['size']}")

        try:
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)

                        # Progress update every 10MB
                        if downloaded % (10 * 1024 * 1024) == 0:
                            progress = (downloaded / total_size) * 100 if total_size > 0 else 0
                            logger.info(".1f")

            logger.info(f"✓ Downloaded {dataset_info['name']} to {filepath}")

            # Extract if compressed
            if filename.endswith(('.zip', '.gz', '.tar.gz')):
                logger.info(f"📦 Extracting {filename}...")
                self.extract_file(filepath)

            return True

        except Exception as e:
            logger.error(f"❌ Error downloading {dataset_info['name']}: {e}")
            if filepath.exists():
                filepath.unlink()  # Clean up partial download
            return False

    def extract_file(self, filepath: Path):
        """Extract compressed files"""
        try:
            if filepath.suffix == '.zip':
                subprocess.run(['powershell', 'Expand-Archive', str(filepath), str(self.data_dir)], check=True)
            elif filepath.suffix == '.gz':
                import gzip
                output_file = filepath.with_suffix('')
                with gzip.open(filepath, 'rb') as f_in:
                    with open(output_file, 'wb') as f_out:
                        f_out.write(f_in.read())
            elif filepath.name.endswith('.tar.gz'):
                import tarfile
                with tarfile.open(filepath, 'r:gz') as tar:
                    tar.extractall(self.data_dir)

            # Remove compressed file after extraction
            filepath.unlink()
            logger.info(f"✓ Extracted {filepath.name}")

        except Exception as e:
            logger.error(f"❌ Error extracting {filepath}: {e}")

    def generate_synthetic_data(self, target_size_gb: float = 10.0) -> bool:
        """Generate synthetic IoT data"""
        import random
        from datetime import datetime, timedelta
        import csv

        logger.info(f"🎲 Generating {target_size_gb}GB synthetic IoT data...")

        # Calculate number of records needed (approx 200 bytes per record)
        bytes_per_record = 200
        target_bytes = target_size_gb * 1024 * 1024 * 1024
        num_records = int(target_bytes / bytes_per_record)

        logger.info(f"   Target: {num_records:,} records")

        output_file = self.data_dir / "synthetic_iot_data.csv"

        # Device configurations
        devices = []
        for i in range(1000):  # 1000 devices
            devices.append({
                'device_id': f"SENSOR_{i:04d}",
                'device_type': random.choice(['temperature', 'humidity', 'pressure', 'motion', 'light']),
                'location': random.choice(['room_1', 'room_2', 'outdoor', 'basement', 'attic'])
            })

        # Generate data
        start_time = datetime.now() - timedelta(days=365)
        current_time = start_time

        try:
            with open(output_file, 'w', newline='') as csvfile:
                fieldnames = ['device_id', 'timestamp', 'temperature', 'humidity', 'pressure',
                            'battery_level', 'signal_strength', 'device_type', 'location']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                batch_size = 10000
                for i in range(0, num_records, batch_size):
                    batch_end = min(i + batch_size, num_records)

                    for j in range(i, batch_end):
                        device = random.choice(devices)
                        current_time += timedelta(seconds=random.randint(1, 60))

                        # Generate sensor readings based on device type
                        if device['device_type'] == 'temperature':
                            temperature = round(random.uniform(15, 35), 2)
                            humidity = round(random.uniform(30, 80), 2)
                            pressure = None
                        elif device['device_type'] == 'humidity':
                            temperature = round(random.uniform(20, 30), 2)
                            humidity = round(random.uniform(20, 90), 2)
                            pressure = None
                        elif device['device_type'] == 'pressure':
                            temperature = round(random.uniform(20, 25), 2)
                            humidity = round(random.uniform(40, 60), 2)
                            pressure = round(random.uniform(980, 1020), 2)
                        else:
                            temperature = round(random.uniform(18, 28), 2)
                            humidity = round(random.uniform(35, 75), 2)
                            pressure = round(random.uniform(990, 1010), 2)

                        row = {
                            'device_id': device['device_id'],
                            'timestamp': current_time.isoformat(),
                            'temperature': temperature,
                            'humidity': humidity,
                            'pressure': pressure,
                            'battery_level': round(random.uniform(10, 100), 2),
                            'signal_strength': random.randint(-90, -30),
                            'device_type': device['device_type'],
                            'location': device['location']
                        }

                        writer.writerow(row)

                    # Progress update
                    progress = (batch_end / num_records) * 100
                    logger.info(".1f")

                    # Checkpoint every 1M records
                    if batch_end % 1000000 == 0:
                        csvfile.flush()
                        logger.info(f"   Checkpoint: {batch_end:,} records written")

            logger.info(f"✓ Generated {target_size_gb}GB synthetic data: {output_file}")
            return True

        except Exception as e:
            logger.error(f"❌ Error generating synthetic data: {e}")
            if output_file.exists():
                output_file.unlink()
            return False

    def list_available_datasets(self):
        """List all available datasets"""
        print("\n📊 CÁC DATASETS IoT SẴN SÀNG TẢI:")
        print("=" * 80)

        for source, datasets in self.datasets.items():
            print(f"\n🔸 Nguồn: {source.upper()}")
            for i, dataset in enumerate(datasets, 1):
                print(f"   {i}. {dataset['name']}")
                print(f"      Size: {dataset['size']}")
                print(f"      Description: {dataset['description']}")
                print()

    def download_dataset(self, source: str, index: int) -> bool:
        """Download specific dataset"""
        if source not in self.datasets:
            logger.error(f"❌ Source '{source}' not found")
            return False

        datasets = self.datasets[source]
        if index < 1 or index > len(datasets):
            logger.error(f"❌ Dataset index {index} not found for source '{source}'")
            return False

        dataset_info = datasets[index - 1]

        if source == "kaggle":
            if not self.setup_kaggle_auth():
                return False
            return self.download_kaggle_dataset(dataset_info)
        elif source == "direct":
            return self.download_direct_file(dataset_info)
        elif source == "generated":
            return self.generate_synthetic_data(10.0)
        else:
            logger.error(f"❌ Unsupported source: {source}")
            return False


def main():
    parser = argparse.ArgumentParser(description="Download 10GB IoT datasets")
    parser.add_argument("--list", action="store_true", help="List available datasets")
    parser.add_argument("--source", choices=["kaggle", "direct", "generated"],
                       help="Data source")
    parser.add_argument("--index", type=int, help="Dataset index to download")
    parser.add_argument("--all-kaggle", action="store_true",
                       help="Download all available Kaggle datasets")
    parser.add_argument("--generate", type=float, default=10.0,
                       help="Generate synthetic data (GB)")

    args = parser.parse_args()

    downloader = IoTDataDownloader()

    if args.list:
        downloader.list_available_datasets()
        return

    if args.generate:
        logger.info(f"🎲 Generating {args.generate}GB synthetic IoT data...")
        success = downloader.generate_synthetic_data(args.generate)
        if success:
            logger.info("✅ Synthetic data generation complete!")
        return

    if args.source and args.index:
        success = downloader.download_dataset(args.source, args.index)
        if success:
            logger.info("✅ Dataset download complete!")
        else:
            logger.error("❌ Dataset download failed!")
        return

    if args.all_kaggle:
        logger.info("📥 Downloading all Kaggle datasets...")
        success_count = 0
        for i, dataset in enumerate(downloader.datasets['kaggle'], 1):
            if downloader.download_dataset('kaggle', i):
                success_count += 1
        logger.info(f"✅ Downloaded {success_count}/{len(downloader.datasets['kaggle'])} Kaggle datasets")
        return

    # Default: show usage
    print("\n🚀 IoT Data Downloader - Tải 10GB Dữ Liệu IoT")
    print("=" * 60)
    print("\n📖 Cách sử dụng:")
    print("  python download_iot_data.py --list                    # Xem datasets có sẵn")
    print("  python download_iot_data.py --source kaggle --index 1  # Tải dataset Kaggle #1")
    print("  python download_iot_data.py --generate 10             # Tạo 10GB data giả")
    print("  python download_iot_data.py --all-kaggle              # Tải tất cả datasets Kaggle")
    print("\n🔧 Setup Kaggle (nếu cần):")
    print("  pip install kaggle")
    print("  kaggle auth login")
    print("\n💡 Khuyến nghị cho 10GB data:")
    print("  1. Dùng --generate 10 để tạo data nhanh")
    print("  2. Hoặc tải multiple Kaggle datasets")
    print("  3. Hoặc dùng --all-kaggle để tải tất cả")


if __name__ == "__main__":
    main()