# AI-Powered IoT Dashboard - Backend System

A production-ready microservices-based backend system for an AI-powered IoT dashboard using FastAPI, PostgreSQL, Redis, Kafka, and MQTT.

## 🏗️ Architecture Overview

This system implements a complete microservices architecture with the following components:

### Services

1. **Chatbot Service** (Port 8001)
   - AI-powered natural language query interface
   - OpenAI GPT-4 integration with MCP (Model Context Protocol)
   - Generates SQL queries from natural language
   - Provides chart configuration recommendations

2. **Query Service** (Port 8002)
   - SQL query execution with validation
   - Redis caching layer for performance
   - Query result optimization
   - Security: Only SELECT statements allowed

3. **Realtime Service** (Port 8003)
   - WebSocket server for real-time data streaming
   - Redis Pub/Sub integration
   - Broadcasts IoT events to connected clients
   - Connection management and heartbeat

4. **Ingestion Service** (Port 8004)
   - MQTT consumer for IoT sensor data
   - Kafka producer for message queuing
   - Data validation and forwarding

5. **Processing Service** (Port 8005)
   - Kafka consumer for data processing
   - Data validation and transformation
   - PostgreSQL storage
   - Redis event publishing

### Infrastructure

- **PostgreSQL**: Primary data store with optimized schema
- **Redis**: Caching and Pub/Sub messaging
- **Kafka**: Message queue for data streaming
- **MQTT**: IoT device communication protocol
- **Zookeeper**: Kafka coordination

## 📊 Data Flow

```
IoT Sensors → MQTT → Ingestion Service → Kafka → Processing Service → PostgreSQL
                                                                      ↓
                                                                    Redis
                                                                      ↓
                                                              Realtime Service
                                                                      ↓
                                                                  WebSocket
                                                                      ↓
                                                                   Clients

User Query → Chatbot Service → LLM (OpenAI) → SQL Generation → Query Service → PostgreSQL/Redis → Results
```

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API Key (for chatbot service)

### Installation

1. Clone the repository:
```bash
cd ai-iot-dashboard
```

2. Configure environment variables:
```bash
# Edit .env file and add your Google Gemini API key
nano .env
# Set: GEMINI_API_KEY=your_api_key_here
# Get your key at: https://makersuite.google.com/app/apikey
```

3. Start all services:
```bash
docker-compose up --build
```

4. Wait for all services to be healthy (check logs):
```bash
docker-compose logs -f
```

### Verify Installation

Check service health:
```bash
# Chatbot Service
curl http://localhost:8001/health

# Query Service
curl http://localhost:8002/health

# Realtime Service
curl http://localhost:8003/health
```

## 📡 API Endpoints

### Chatbot Service (Port 8001)

**POST /api/v1/chatbot/chat**
```json
{
  "prompt": "Show me the average temperature for all sensors in the last 24 hours",
  "session_id": "optional-session-id"
}
```

Response:
```json
{
  "message": "Found 5 result(s) from database",
  "sql": "SELECT device_id, AVG(temperature) as avg_temp FROM logs WHERE timestamp > NOW() - INTERVAL '24 hours' GROUP BY device_id",
  "data": [
    {"device_id": "SENSOR_001", "avg_temp": 22.5}
  ],
  "chart": {
    "type": "bar",
    "x": "device_id",
    "y": "avg_temp",
    "title": "Average Temperature by Device"
  },
  "source": "database",
  "execution_time": 0.125
}
```

### Query Service (Port 8002)

**POST /api/v1/query/execute**
```json
{
  "sql": "SELECT * FROM devices LIMIT 10",
  "use_cache": true
}
```

Response:
```json
{
  "data": [...],
  "row_count": 10,
  "source": "cache",
  "execution_time": 0.015,
  "cached": true
}
```

### Realtime Service (Port 8003)

**WebSocket: ws://localhost:8003/api/v1/realtime/ws**

Connect to receive real-time IoT events:
```javascript
const ws = new WebSocket('ws://localhost:8003/api/v1/realtime/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

## 🔧 Scripts

### Stream IoT Data

Stream sample data from CSV:
```bash
docker exec -it processing-service python /app/scripts/stream_from_csv.py --csv /app/scripts/sample_data.csv
```

Generate random IoT data:
```bash
docker exec -it processing-service python /app/scripts/stream_from_csv.py --generate --duration 60
```

### Aggregate Daily Statistics

Aggregate yesterday's data:
```bash
docker exec -it processing-service python /app/scripts/aggregate_daily.py --yesterday
```

Aggregate specific date:
```bash
docker exec -it processing-service python /app/scripts/aggregate_daily.py --date 2024-01-15
```

Aggregate last 7 days:
```bash
docker exec -it processing-service python /app/scripts/aggregate_daily.py --days 7
```

## 🗄️ Database Schema

### Tables

1. **devices**: Device registry
   - device_id (PK)
   - device_name, device_type, location, status
   - metadata (JSONB)

2. **logs**: IoT sensor readings
   - log_id (PK)
   - device_id (FK)
   - timestamp, temperature, humidity, pressure
   - battery_level, signal_strength, status
   - metadata (JSONB)

3. **daily_stats**: Aggregated daily statistics
   - stat_id (PK)
   - device_id (FK), date
   - avg/min/max for temperature, humidity, pressure, battery_level
   - record_count

4. **alerts**: Alert records
   - alert_id (PK)
   - device_id (FK)
   - alert_type, severity, message
   - threshold_value, actual_value
   - acknowledged, resolved

### Indexes

Optimized indexes for:
- Device lookups
- Time-range queries
- Device + timestamp combinations
- Status filtering

## 🔐 Security Features

- SQL injection prevention (only SELECT allowed)
- Input validation with Pydantic
- Environment variable configuration
- Connection pooling with limits
- Query timeout protection
- Redis password authentication

## 📈 Performance Optimizations

- Redis caching with TTL
- Database connection pooling
- Kafka message batching
- Indexed database queries
- Materialized views for summaries
- WebSocket connection limits

## 🐛 Troubleshooting

### Services not starting

Check logs:
```bash
docker-compose logs [service-name]
```

### Database connection issues

Verify PostgreSQL is running:
```bash
docker-compose ps postgres
docker-compose logs postgres
```

### Kafka connection issues

Ensure Kafka and Zookeeper are healthy:
```bash
docker-compose ps kafka zookeeper
docker-compose logs kafka
```

### Redis connection issues

Check Redis status:
```bash
docker-compose ps redis
docker-compose exec redis redis-cli -a redis_password_2024 ping
```

## 🧪 Testing

### Test MQTT Ingestion

Publish test message:
```bash
docker-compose exec mqtt mosquitto_pub -h localhost -t "iot/sensors/test" -m '{"device_id":"SENSOR_001","temperature":22.5,"humidity":45.0}'
```

### Test Kafka

Check Kafka topics:
```bash
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

Consume messages:
```bash
docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic iot_logs --from-beginning
```

### Test Database

Connect to PostgreSQL:
```bash
docker-compose exec postgres psql -U iot_user -d iot_dashboard
```

Query data:
```sql
SELECT COUNT(*) FROM logs;
SELECT * FROM devices;
SELECT * FROM daily_stats ORDER BY date DESC LIMIT 10;
```

## 📊 Monitoring

### Service Status

```bash
# Check all services
docker-compose ps

# View logs
docker-compose logs -f [service-name]

# Check resource usage
docker stats
```

### Database Monitoring

```sql
-- Active connections
SELECT count(*) FROM pg_stat_activity;

-- Table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Recent logs
SELECT COUNT(*), DATE(timestamp) FROM logs GROUP BY DATE(timestamp) ORDER BY DATE(timestamp) DESC;
```

## 🛠️ Development

### Adding New Services

1. Create service directory under `services/`
2. Follow the standard structure:
   - `app/controllers/` - API endpoints
   - `app/services/` - Business logic
   - `app/repositories/` - Data access
   - `app/models/` - Schemas
   - `app/core/` - Configuration
3. Add Dockerfile and requirements.txt
4. Update docker-compose.yml

### Environment Variables

Each service has its own `.env` file. Main configuration in root `.env`:
- Database credentials
- Redis configuration
- Kafka settings
- MQTT broker
- Service ports
- OpenAI API key

## 📝 License

This project is provided as-is for educational and commercial use.

## 🤝 Contributing

This is a production-ready template. Customize for your specific needs:
- Add authentication/authorization
- Implement rate limiting
- Add monitoring (Prometheus, Grafana)
- Implement logging aggregation (ELK stack)
- Add API gateway
- Implement service mesh

## 📞 Support

For issues and questions:
1. Check logs: `docker-compose logs [service]`
2. Verify configuration in `.env` files
3. Ensure all prerequisites are installed
4. Check service health endpoints

## 🎯 Next Steps

1. Configure Google Gemini API key (see GEMINI_MIGRATION.md)
2. Start services with `docker-compose up`
3. Test chatbot with natural language queries
4. Stream sample IoT data
5. Connect WebSocket client for real-time updates
6. Customize for your use case
7. Run performance tests: `python scripts/test_gemini.py`
