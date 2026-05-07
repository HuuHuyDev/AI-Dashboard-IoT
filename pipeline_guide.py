#!/usr/bin/env python3
"""
Hướng Dẫn Chi Tiết: Pipeline Kaggle → MQTT → Kafka → Database
Script này sẽ hướng dẫn từng bước xử lý 10GB dữ liệu IoT
"""
import os
import sys
import subprocess
import time
from pathlib import Path
import json
import pandas as pd
from datetime import datetime

class IoTPipelineGuide:
    """Hướng dẫn pipeline IoT từ A đến Z"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.data_dir = self.project_root / "data"
        self.data_dir.mkdir(exist_ok=True)

        print("🚀 IoT Pipeline Guide - Xử Lý 10GB Dữ Liệu")
        print("=" * 60)

    def step_1_setup_kaggle(self):
        """Bước 1: Cài đặt Kaggle và tải dữ liệu"""
        print("\n📥 BƯỚC 1: CÀI ĐẶT KAGGLE & TẢI DỮ LIỆU")
        print("-" * 50)

        # Kiểm tra kaggle
        try:
            subprocess.run(["kaggle", "--version"], check=True, capture_output=True)
            print("✓ Kaggle CLI đã cài đặt")
        except:
            print("❌ Cần cài đặt Kaggle CLI:")
            print("   pip install kaggle")
            print("   Hoặc: conda install -c conda-forge kaggle")
            return False

        # Kiểm tra API key
        kaggle_dir = Path.home() / ".kaggle"
        api_key = kaggle_dir / "kaggle.json"

        if not api_key.exists():
            print("❌ Cần thiết lập Kaggle API key:")
            print("   1. Vào https://www.kaggle.com/account")
            print("   2. Tạo New API Token")
            print("   3. Download kaggle.json")
            print(f"   4. Copy vào: {kaggle_dir}/")
            print("   5. Chạy: chmod 600 ~/.kaggle/kaggle.json")
            return False

        print("✓ Kaggle API key đã thiết lập")

        # Tìm dataset IoT
        print("\n🔍 Tìm dataset IoT trên Kaggle:")
        print("Ví dụ các dataset phù hợp:")
        print("  - kaggle datasets list --search 'iot sensor'")
        print("  - kaggle datasets list --search 'time series'")
        print("  - kaggle datasets list --search 'smart home'")

        # Ví dụ download dataset
        print("\n💡 Ví dụ download dataset:")
        print("  kaggle datasets download -d vikassingh1996/iot-time-series-data -p data/")
        print("  unzip data/iot-time-series-data.zip -d data/")

        return True

    def step_2_prepare_data(self):
        """Bước 2: Chuẩn bị dữ liệu"""
        print("\n📋 BƯỚC 2: CHUẨN BỊ DỮ LIỆU")
        print("-" * 50)

        # Tạo thư mục data
        print(f"📁 Tạo thư mục data: {self.data_dir}")
        self.data_dir.mkdir(exist_ok=True)

        # Ví dụ cấu trúc file
        print("\n📂 Cấu trúc file sau khi download:")
        print("data/")
        print("├── iot_dataset.csv          # File chính 10GB")
        print("├── sample_data.csv          # File mẫu nhỏ")
        print("└── metadata.json            # Thông tin dataset")

        # Validate file
        csv_files = list(self.data_dir.glob("*.csv"))
        if csv_files:
            print(f"\n✓ Tìm thấy {len(csv_files)} file CSV:")
            for csv_file in csv_files:
                size_mb = csv_file.stat().st_size / 1024 / 1024
                print(".2f")
        else:
            print("\n❌ Chưa có file CSV nào trong thư mục data/")
            print("Hãy download dataset trước!")

        return bool(csv_files)

    def step_3_start_services(self):
        """Bước 3: Khởi động các service"""
        print("\n🐳 BƯỚC 3: KHỞI ĐỘNG CÁC SERVICE")
        print("-" * 50)

        print("📍 Vào thư mục dự án:")
        print(f"   cd {self.project_root}")

        print("\n🚀 Khởi động tất cả services:")
        print("   docker-compose up -d --build")

        print("\n⏳ Chờ services khởi động (khoảng 2-3 phút)...")
        print("   docker-compose logs -f | head -50")

        print("\n🔍 Kiểm tra services healthy:")
        print("   docker-compose ps")
        print("   curl http://localhost:8004/health  # Ingestion")
        print("   curl http://localhost:8005/health  # Processing")

        return True

    def step_4_publish_mqtt(self):
        """Bước 4: Publish dữ liệu qua MQTT"""
        print("\n📤 BƯỚC 4: PUBLISH DỮ LIỆU QUA MQTT")
        print("-" * 50)

        # Tìm file CSV
        csv_files = list(self.data_dir.glob("*.csv"))
        if not csv_files:
            print("❌ Không tìm thấy file CSV nào!")
            return False

        # Chọn file chính (lớn nhất)
        main_file = max(csv_files, key=lambda f: f.stat().st_size)
        print(f"📄 File chính: {main_file}")
        print(".2f")

        # Kiểm tra cấu trúc file
        print("\n🔍 Kiểm tra cấu trúc file:")
        try:
            df = pd.read_csv(main_file, nrows=5)
            print("Cột có trong file:")
            for i, col in enumerate(df.columns, 1):
                print(f"   {i}. {col}")
        except Exception as e:
            print(f"❌ Lỗi đọc file: {e}")
            return False

        # Script publish MQTT
        publish_script = self.project_root / "scripts" / "publish_to_mqtt.py"
        if not publish_script.exists():
            print(f"❌ Không tìm thấy script: {publish_script}")
            return False

        print("🛠️ Chạy script publish MQTT:")
        print(f"   python {publish_script} --file {main_file} --batch 200 --resume")
        print("   # --batch 200: Gửi 200 bản tin mỗi lần")
        print("   # --resume: Tiếp tục từ checkpoint nếu bị gián đoạn")

        print("\n⏳ Thời gian ước tính:")
        print("   - 10GB dữ liệu: ~10-15 phút")
        print("   - 1GB dữ liệu: ~1-2 phút")
        print("   - Tốc độ: ~5000-10000 bản tin/phút")

        return True

    def step_5_monitor_pipeline(self):
        """Bước 5: Giám sát pipeline"""
        print("\n📊 BƯỚC 5: GIÁM SÁT PIPELINE")
        print("-" * 50)

        monitor_script = self.project_root / "scripts" / "monitor_pipeline.py"
        if monitor_script.exists():
            print("🖥️ Chạy script giám sát:")
            print(f"   python {monitor_script}")
        else:
            print("📋 Giám sát thủ công:")

        print("\n🔍 Kiểm tra MQTT messages:")
        print("   docker-compose logs -f ingestion-service | grep 'Received message'")

        print("\n🔍 Kiểm tra Kafka:")
        print("   docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic iot_logs --from-beginning | head -10")

        print("\n🔍 Kiểm tra database:")
        print("   docker-compose exec processing-db psql -U processing_user -d processing_db -c 'SELECT COUNT(*) FROM logs;'")

        print("\n📈 Metrics quan trọng:")
        print("   - MQTT: messages/second")
        print("   - Kafka: lag, throughput")
        print("   - DB: insert rate, total records")

    def step_6_verify_results(self):
        """Bước 6: Kiểm tra kết quả"""
        print("\n✅ BƯỚC 6: KIỂM TRA KẾT QUẢ")
        print("-" * 50)

        print("🔍 Kiểm tra số bản ghi trong database:")
        print("   docker-compose exec processing-db psql -U processing_user -d processing_db -c 'SELECT COUNT(*) FROM logs;'")

        print("\n🔍 Kiểm tra devices:")
        print("   docker-compose exec processing-db psql -U processing_user -d processing_db -c 'SELECT device_id, COUNT(*) FROM logs GROUP BY device_id;'")

        print("\n🔍 Kiểm tra daily stats:")
        print("   docker-compose exec processing-db psql -U processing_user -d processing_db -c 'SELECT * FROM daily_stats LIMIT 5;'")

        print("\n🔍 Test API Query:")
        print("   curl -X POST http://localhost:8002/api/v1/query/execute \\")
        print("     -H 'Content-Type: application/json' \\")
        print("     -d '{\"sql\": \"SELECT device_id, COUNT(*) FROM logs GROUP BY device_id\", \"use_cache\": true}'")

        print("\n🔍 Test Chatbot:")
        print("   curl -X POST http://localhost:8001/api/v1/chatbot/chat \\")
        print("     -H 'Content-Type: application/json' \\")
        print("     -d '{\"prompt\": \"Show me the average temperature for all sensors\"}'")

    def create_sample_data(self):
        """Tạo dữ liệu mẫu để test"""
        print("\n🎯 TẠO DỮ LIỆU MẪU ĐỂ TEST")
        print("-" * 50)

        sample_file = self.data_dir / "sample_data.csv"

        if sample_file.exists():
            print(f"✓ File mẫu đã tồn tại: {sample_file}")
            return

        print("📝 Tạo file mẫu 1000 bản ghi...")

        import random
        from datetime import datetime, timedelta

        devices = ["SENSOR_001", "SENSOR_002", "SENSOR_003", "SENSOR_004", "SENSOR_005"]
        start_time = datetime.now() - timedelta(days=1)

        with open(sample_file, 'w') as f:
            f.write("device_id,timestamp,temperature,humidity,pressure,battery_level,signal_strength\n")

            for i in range(1000):
                device = random.choice(devices)
                timestamp = start_time + timedelta(minutes=i*5)
                temp = round(random.uniform(20, 30), 1)
                humidity = random.randint(40, 80)
                pressure = round(random.uniform(1000, 1020), 1)
                battery = random.randint(70, 100)
                signal = random.randint(-50, -20)

                f.write(f"{device},{timestamp.isoformat()},{temp},{humidity},{pressure},{battery},{signal}\n")

        print(f"✓ Tạo xong: {sample_file}")
        print("   1000 bản ghi, 5 devices, dữ liệu ngẫu nhiên")

    def run_full_pipeline(self):
        """Chạy toàn bộ pipeline"""
        print("\n🎬 CHẠY TOÀN BỘ PIPELINE")
        print("=" * 60)

        steps = [
            ("Setup Kaggle", self.step_1_setup_kaggle),
            ("Prepare Data", self.step_2_prepare_data),
            ("Start Services", self.step_3_start_services),
            ("Publish MQTT", self.step_4_publish_mqtt),
            ("Monitor Pipeline", self.step_5_monitor_pipeline),
            ("Verify Results", self.step_6_verify_results),
        ]

        for step_name, step_func in steps:
            print(f"\n🔸 {step_name}")
            try:
                if not step_func():
                    print(f"❌ {step_name} thất bại!")
                    break
                print(f"✅ {step_name} hoàn thành!")
            except Exception as e:
                print(f"❌ Lỗi trong {step_name}: {e}")
                break

    def show_troubleshooting(self):
        """Hướng dẫn khắc phục sự cố"""
        print("\n🔧 TROUBLESHOOTING")
        print("=" * 60)

        issues = {
            "MQTT không kết nối": [
                "Kiểm tra MQTT broker chạy: docker-compose ps | grep mosquitto",
                "Kiểm tra port 1883 không bị chiếm: netstat -an | grep 1883",
                "Restart MQTT: docker-compose restart mosquitto"
            ],

            "Kafka không nhận message": [
                "Kiểm tra Kafka chạy: docker-compose ps | grep kafka",
                "Kiểm tra topic: docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092",
                "Tạo topic nếu thiếu: docker-compose exec kafka kafka-topics --create --topic iot_logs --bootstrap-server localhost:9092"
            ],

            "Database không ghi được": [
                "Kiểm tra DB chạy: docker-compose ps | grep processing-db",
                "Kiểm tra connection: docker-compose exec processing-db pg_isready -U processing_user -d processing_db",
                "Xem logs: docker-compose logs processing-service"
            ],

            "Out of memory": [
                "Giảm batch size trong scripts",
                "Tăng RAM cho Docker (Docker Desktop > Settings > Resources)",
                "Xử lý file theo chunk nhỏ hơn"
            ]
        }

        for issue, solutions in issues.items():
            print(f"\n❌ {issue}:")
            for sol in solutions:
                print(f"   • {sol}")

    def show_performance_tips(self):
        """Tips tối ưu performance"""
        print("\n⚡ PERFORMANCE TIPS")
        print("=" * 60)

        tips = {
            "MQTT": [
                "Dùng QoS=1 thay vì QoS=2 để tăng tốc",
                "Batch 100-500 messages thay vì gửi từng cái",
                "Tăng MQTT keepalive interval"
            ],

            "Kafka": [
                "Tăng batch.size và linger.ms",
                "Bật compression (gzip)",
                "Tăng num.partitions cho topic iot_logs"
            ],

            "Database": [
                "Dùng COPY thay vì INSERT loops",
                "Tăng connection pool size",
                "VACUUM ANALYZE định kỳ"
            ],

            "Processing": [
                "Tăng số worker threads",
                "Batch processing 5000+ messages",
                "Async I/O cho tất cả operations"
            ]
        }

        for component, tips_list in tips.items():
            print(f"\n🔧 {component}:")
            for tip in tips_list:
                print(f"   • {tip}")


def main():
    guide = IoTPipelineGuide()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "sample":
            guide.create_sample_data()
        elif command == "monitor":
            guide.step_5_monitor_pipeline()
        elif command == "verify":
            guide.step_6_verify_results()
        elif command == "troubleshoot":
            guide.show_troubleshooting()
        elif command == "tips":
            guide.show_performance_tips()
        else:
            print("Commands: sample, monitor, verify, troubleshoot, tips")
    else:
        guide.run_full_pipeline()


if __name__ == "__main__":
    main()