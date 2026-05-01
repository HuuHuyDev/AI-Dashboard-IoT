# Implementation Plan: Team Deployment Workflow - AI IoT Dashboard

## Overview

Phân công công việc chi tiết cho 5 thành viên team để triển khai AI IoT Dashboard với 2 luồng chính:
1. **IoT Data Pipeline**: IoT → MQTT → Kafka → Processing → PostgreSQL → Redis Pub/Sub → WebSocket → Frontend
2. **AI Query Pipeline**: User → Chatbot → LLM (MCP) → SQL → Query Service → DB → Chart

Mỗi thành viên có thể làm việc độc lập trên service của mình, với các integration points rõ ràng.

---

## 🔧 Tasks Chung - Setup & Infrastructure (Tất cả thành viên)

- [ ] 0. Setup môi trường development
  - Clone repository và checkout branch riêng
  - Cài đặt Docker và Docker Compose
  - Verify tất cả services start successfully: `docker-compose up -d`
  - Test kết nối đến PostgreSQL, Redis, Kafka, MQTT
  - _Blocking: Tất cả tasks khác_

- [ ] 1. Cấu hình environment variables
  - Copy `.env.example` thành `.env` cho từng service
  - Cấu hình API keys (Gemini API key cho Chatbot Service)
  - Cấu hình database credentials
  - Verify environment variables được load đúng
  - _Blocking: Service-specific tasks_

---

## 👤 Thành Viên HUY: Chatbot Service - Gemini MCP Integration

### Phase 1: Setup Gemini API với MCP

- [ ] 2. Setup Gemini API và MCP tools
  - [ ] 2.1 Cài đặt Google Generative AI SDK
    - Add `google-generativeai` vào `requirements.txt`
    - Install dependencies: `pip install -r requirements.txt`
    - _Service: Chatbot Service_
  
  - [ ] 2.2 Implement MCP tool definition cho SQL generation
    - Tạo file `app/services/llm_service.py`
    - Define MCP tool schema với function `generate_sql`
    - Parameters: sql (string), chart_type (enum), x_axis, y_axis, chart_title
    - Test tool definition với Gemini API
    - _Service: Chatbot Service_
    - _Reference: TEAM_ASSIGNMENT.md - MCP Implementation Guide_
  
  - [ ] 2.3 Implement system prompt với database schema context
    - Include database schema (devices, logs, daily_stats, alerts tables)
    - Add SQL generation rules (only SELECT, PostgreSQL syntax)
    - Add safety constraints (no DROP/DELETE/UPDATE)
    - Test với sample prompts
    - _Service: Chatbot Service_

- [ ] 3. Implement SQL generation logic
  - [ ] 3.1 Create LLM service class
    - Implement `generate_sql()` method
    - Configure Gemini model (gemini-1.5-pro)
    - Set temperature=0.1 for consistent SQL generation
    - Handle API errors và retries
    - _Service: Chatbot Service_
  
  - [ ] 3.2 Parse MCP function call responses
    - Extract SQL query từ function call
    - Extract chart configuration
    - Validate response structure
    - Handle cases where Gemini doesn't call tool
    - _Service: Chatbot Service_
  
  - [ ]* 3.3 Write unit tests cho SQL generation
    - Test với 10+ different natural language prompts
    - Test edge cases (ambiguous queries, invalid requests)
    - Test SQL validation logic
    - Verify chart type recommendations
    - _Service: Chatbot Service_

### Phase 2: Chart Recommendation Logic

- [ ] 4. Implement intelligent chart recommendations
  - [ ] 4.1 Create chart recommendation engine
    - Time series data → line chart
    - Device comparisons → bar chart
    - Percentages → pie chart
    - Correlations → scatter chart
    - _Service: Chatbot Service_
  
  - [ ] 4.2 Auto-detect axes from SQL results
    - Parse SQL SELECT clause
    - Identify X and Y axis columns
    - Generate meaningful chart titles
    - Handle cases where chart is not applicable
    - _Service: Chatbot Service_

### Phase 3: Integration với Query Service

- [ ] 5. Implement Query Service integration
  - [ ] 5.1 Create HTTP client cho Query Service
    - Use httpx for async HTTP calls
    - Endpoint: `POST http://query-service:8002/api/v1/query/execute`
    - Implement request/response models
    - _Service: Chatbot Service_
    - _Blocking: Thành viên 2 - Task 11_
  
  - [ ] 5.2 Implement error handling và retries
    - Handle timeouts (30s)
    - Implement retry logic (3 retries with exponential backoff)
    - Handle Query Service errors
    - Log all API calls
    - _Service: Chatbot Service_
  
  - [ ] 5.3 Build complete chatbot response
    - Combine SQL, data results, and chart config
    - Format response for frontend
    - Add explanation text
    - _Service: Chatbot Service_

- [ ] 6. Checkpoint - Test Chatbot Service end-to-end
  - Test với Swagger UI: http://localhost:8001/docs
  - Test 20+ different natural language queries
  - Verify SQL generation accuracy
  - Verify chart recommendations
  - Verify integration với Query Service
  - Ensure all tests pass, ask the user if questions arise.

---

## 👤 Thành Viên TRUNG Query Service - SQL Execution & Caching

### Phase 1: SQL Execution Engine

- [ ] 7. Implement SQL validation và execution
  - [ ] 7.1 Create SQL validator
    - Validate only SELECT statements allowed
    - Block DROP, DELETE, UPDATE, INSERT commands
    - Validate SQL syntax
    - Prevent SQL injection
    - _Service: Query Service_
  
  - [ ] 7.2 Setup PostgreSQL connection pool
    - Configure SQLAlchemy engine
    - Set pool size (min=5, max=20)
    - Implement connection lifecycle management
    - Handle connection errors và reconnection
    - _Service: Query Service_
  
  - [ ] 7.3 Implement query execution logic
    - Execute validated SQL queries
    - Handle query timeouts (30s)
    - Parse và format results
    - Return row count và execution time
    - _Service: Query Service_
  
  - [ ]* 7.4 Write unit tests cho SQL execution
    - Test valid SELECT queries
    - Test blocked commands (DROP, DELETE)
    - Test SQL injection attempts
    - Test timeout handling
    - _Service: Query Service_

### Phase 2: Redis Caching Layer

- [ ] 8. Implement Redis caching strategy
  - [ ] 8.1 Setup Redis client
    - Configure Redis connection
    - Implement connection pooling
    - Handle Redis connection errors
    - _Service: Query Service_
  
  - [ ] 8.2 Implement cache key generation
    - Generate hash từ SQL query
    - Include query parameters in hash
    - Implement cache key prefix strategy
    - _Service: Query Service_
  
  - [ ] 8.3 Implement cache read/write logic
    - Check cache before executing query
    - Store query results in cache
    - Set TTL (300 seconds default)
    - Handle cache misses
    - _Service: Query Service_
  
  - [ ] 8.4 Add cache metrics
    - Track cache hit rate
    - Track cache miss rate
    - Log cache performance
    - _Service: Query Service_

### Phase 3: API Endpoints

- [ ] 9. Create Query Service API endpoints
  - [ ] 9.1 Implement POST /api/v1/query/execute
    - Accept SQL query và options
    - Validate request
    - Execute query với caching
    - Return results với metadata
    - _Service: Query Service_
  
  - [ ] 9.2 Implement GET /api/v1/query/health
    - Check database connection
    - Check Redis connection
    - Return service health status
    - _Service: Query Service_
  
  - [ ]* 9.3 Write integration tests
    - Test API endpoints với valid queries
    - Test caching behavior
    - Test error responses
    - Load test với concurrent requests
    - _Service: Query Service_

- [ ] 10. Checkpoint - Test Query Service
  - Test với Swagger UI: http://localhost:8002/docs
  - Verify SQL execution works
  - Verify Redis caching (check cache hit/miss)
  - Test response time < 100ms (cached), < 500ms (uncached)
  - Test concurrent requests (50+ simultaneous)
  - Ensure all tests pass, ask the user if questions arise.

---

## 👤 Thành Viên SÁNG: Realtime Service - WebSocket & Broadcasting

### Phase 1: WebSocket Server

- [ ] 11. Implement WebSocket server
  - [ ] 11.1 Create WebSocket endpoint
    - Endpoint: `ws://localhost:8003/api/v1/realtime/ws`
    - Accept WebSocket connections
    - Send welcome message on connect
    - _Service: Realtime Service_
  
  - [ ] 11.2 Implement connection management
    - Track active connections in memory
    - Add connection to pool on connect
    - Remove connection on disconnect
    - Implement connection limits (max 1000)
    - _Service: Realtime Service_
  
  - [ ] 11.3 Implement heartbeat mechanism
    - Send heartbeat every 30 seconds
    - Detect dead connections
    - Auto-cleanup stale connections
    - _Service: Realtime Service_
  
  - [ ]* 11.4 Write unit tests cho WebSocket
    - Test connection/disconnection
    - Test heartbeat mechanism
    - Test connection limits
    - Test error handling
    - _Service: Realtime Service_

### Phase 2: Redis Pub/Sub Integration

- [ ] 12. Implement Redis Pub/Sub subscriber
  - [ ] 12.1 Setup Redis Pub/Sub client
    - Configure Redis connection
    - Subscribe to channel: `iot_events`
    - Handle subscription errors
    - _Service: Realtime Service_
    - _Blocking: Thành viên 5 - Task 22_
  
  - [ ] 12.2 Implement message handler
    - Receive messages từ Redis
    - Parse message payload
    - Validate message structure
    - Log received messages
    - _Service: Realtime Service_
  
  - [ ] 12.3 Implement broadcasting logic
    - Broadcast to all connected clients
    - Format messages for WebSocket
    - Handle broadcast errors
    - Track broadcast metrics
    - _Service: Realtime Service_

### Phase 3: Testing & Optimization

- [ ] 13. Test và optimize Realtime Service
  - [ ] 13.1 Create HTML test client
    - Simple HTML page với WebSocket connection
    - Display real-time messages
    - Show connection status
    - _Service: Realtime Service_
  
  - [ ]* 13.2 Load testing
    - Test với 100+ concurrent connections
    - Measure broadcast latency (target < 100ms)
    - Test reconnection logic
    - Monitor memory usage
    - _Service: Realtime Service_

- [ ] 14. Checkpoint - Test Realtime Service
  - Test WebSocket connection với HTML client
  - Verify real-time broadcasting works
  - Test với multiple clients
  - Verify heartbeat mechanism
  - Test reconnection after disconnect
  - Ensure all tests pass, ask the user if questions arise.

---

## 👤 Thành Viên PHƯƠNG: Ingestion Service - Kaggle Data & MQTT

### Phase 1: Kaggle API Integration

- [ ] 15. Setup Kaggle API và download dataset
  - [ ] 15.1 Configure Kaggle API credentials
    - Install kaggle package: `pip install kaggle`
    - Setup kaggle.json credentials
    - Test Kaggle API connection
    - _Service: Ingestion Service_
  
  - [ ] 15.2 Download IoT sensor dataset
    - Choose dataset: `garystafford/environmental-sensor-data-132k`
    - Implement dataset downloader class
    - Download và unzip dataset
    - Verify CSV file structure
    - _Service: Ingestion Service_
    - _Reference: TEAM_ASSIGNMENT.md - Kaggle Data Ingestion Guide_

### Phase 2: Data Streaming Service

- [ ] 16. Implement Kaggle data streamer
  - [ ] 16.1 Create CSV reader với pandas
    - Read CSV file in chunks
    - Parse sensor data columns
    - Handle large files efficiently
    - _Service: Ingestion Service_
  
  - [ ] 16.2 Implement data validation
    - Validate temperature range (-50 to 100°C)
    - Validate humidity range (0 to 100%)
    - Validate pressure range (900 to 1100 hPa)
    - Validate battery level (0 to 100%)
    - Log validation errors
    - _Service: Ingestion Service_
  
  - [ ] 16.3 Implement data transformation
    - Convert data types
    - Add metadata (ingestion_timestamp, source)
    - Handle missing values
    - Format for Kafka
    - _Service: Ingestion Service_
  
  - [ ]* 16.4 Write unit tests cho data validation
    - Test valid sensor data
    - Test invalid data (out of range)
    - Test missing values
    - Test data transformation
    - _Service: Ingestion Service_

### Phase 3: Kafka Producer Integration

- [ ] 17. Implement Kafka producer
  - [ ] 17.1 Setup Kafka producer
    - Configure Kafka connection (kafka:9092)
    - Set serialization (JSON)
    - Configure acks='all' for reliability
    - Set retries=3
    - _Service: Ingestion Service_
  
  - [ ] 17.2 Implement streaming logic
    - Stream data từ CSV với configurable interval
    - Send messages to Kafka topic: `iot_logs`
    - Add progress tracking
    - Handle Kafka errors
    - _Service: Ingestion Service_
    - _Blocking: Thành viên 5 - Task 19_
  
  - [ ] 17.3 Add monitoring và metrics
    - Track messages sent
    - Track validation errors
    - Track Kafka producer metrics
    - Log streaming progress
    - _Service: Ingestion Service_

### Phase 4: MQTT Consumer (Bonus)

- [ ] 18. Implement MQTT consumer
  - [ ] 18.1 Setup MQTT client
    - Configure MQTT connection (mosquitto:1883)
    - Subscribe to topic: `iot/sensors/#`
    - Handle connection errors
    - _Service: Ingestion Service_
  
  - [ ] 18.2 Forward MQTT messages to Kafka
    - Receive MQTT messages
    - Validate và transform
    - Send to Kafka
    - Handle errors
    - _Service: Ingestion Service_

- [ ] 19. Checkpoint - Test Ingestion Service
  - Verify Kaggle dataset downloaded
  - Test data streaming từ CSV
  - Monitor Kafka topic: `docker-compose exec kafka kafka-console-consumer --topic iot_logs`
  - Verify data validation works
  - Test streaming performance (records/second)
  - Ensure all tests pass, ask the user if questions arise.

---

## 👤 Thành Viên AN: Processing Service - Kafka Consumer & Data Storage

### Phase 1: Kafka Consumer

- [ ] 20. Implement Kafka consumer
  - [ ] 20.1 Setup Kafka consumer
    - Configure Kafka connection
    - Consumer group: `processing-service`
    - Subscribe to topic: `iot_logs`
    - Configure auto-commit=False for manual control
    - _Service: Processing Service_
  
  - [ ] 20.2 Implement message consumption logic
    - Consume messages từ Kafka
    - Parse JSON payload
    - Handle deserialization errors
    - Implement offset management
    - _Service: Processing Service_
  
  - [ ]* 20.3 Write unit tests cho Kafka consumer
    - Test message consumption
    - Test error handling
    - Test offset management
    - _Service: Processing Service_

### Phase 2: Data Processing & Storage

- [ ] 21. Implement data processing logic
  - [ ] 21.1 Create data validation service
    - Validate sensor data ranges
    - Check for duplicates
    - Data quality checks
    - _Service: Processing Service_
  
  - [ ] 21.2 Implement database repository
    - Create log_repository.py
    - Implement INSERT logic cho logs table
    - Use batch inserts for performance
    - Handle database errors
    - _Service: Processing Service_
  
  - [ ] 21.3 Implement transaction management
    - Wrap database operations in transactions
    - Commit Kafka offset only after successful DB insert
    - Implement rollback on errors
    - Ensure exactly-once semantics
    - _Service: Processing Service_
  
  - [ ]* 21.4 Write integration tests
    - Test Kafka → Database pipeline
    - Test batch inserts
    - Test error handling
    - Test transaction rollback
    - _Service: Processing Service_

### Phase 3: Redis Event Publishing

- [ ] 22. Implement Redis event publisher
  - [ ] 22.1 Setup Redis publisher
    - Configure Redis connection
    - Implement publish method
    - Handle Redis errors
    - _Service: Processing Service_
  
  - [ ] 22.2 Publish events after DB insert
    - Publish to channel: `iot_events`
    - Format event payload
    - Include device_id và data
    - Log published events
    - _Service: Processing Service_
    - _Blocking: Thành viên 3 - Task 12_
  
  - [ ]* 22.3 Write integration tests
    - Test Redis publishing
    - Verify event format
    - Test error handling
    - _Service: Processing Service_

### Phase 4: Daily Aggregation

- [ ] 23. Implement daily aggregation scripts
  - [ ] 23.1 Create aggregation script
    - Calculate daily statistics (avg, min, max temperature)
    - Insert into daily_stats table
    - Handle date ranges
    - _Service: Processing Service_
  
  - [ ] 23.2 Setup scheduled job
    - Run daily at midnight
    - Use cron or scheduler
    - Log execution results
    - _Service: Processing Service_

- [ ] 24. Checkpoint - Test Processing Service
  - Verify Kafka consumption works
  - Check data inserted into PostgreSQL: `SELECT COUNT(*) FROM logs`
  - Verify Redis events published
  - Test end-to-end flow: Ingestion → Kafka → Processing → DB → Redis → Realtime
  - Run aggregation script manually
  - Ensure all tests pass, ask the user if questions arise.

---

## 🔗 Integration Testing (Tất cả thành viên)

- [ ] 25. End-to-end integration testing
  - [ ] 25.1 Test IoT Data Pipeline
    - Start all services
    - Stream data từ Kaggle (Thành viên 4)
    - Verify data flows through Kafka
    - Verify data stored in PostgreSQL (Thành viên 5)
    - Verify real-time events broadcasted (Thành viên 3)
    - _Blocking: Tasks 19, 24, 14_
  
  - [ ] 25.2 Test AI Query Pipeline
    - Send natural language query to Chatbot (Thành viên 1)
    - Verify SQL generated correctly
    - Verify query executed (Thành viên 2)
    - Verify results returned với chart config
    - Test caching behavior
    - _Blocking: Tasks 6, 10_
  
  - [ ]* 25.3 Load testing
    - Simulate 100+ concurrent users
    - Stream 1000+ IoT messages/second
    - Monitor system performance
    - Identify bottlenecks
    - _All services_

- [ ] 26. Final checkpoint - System verification
  - All services running: `docker-compose ps`
  - All health checks passing
  - No errors in logs
  - Test với real user scenarios
  - Performance meets requirements
  - Ensure all tests pass, ask the user if questions arise.

---

## 📚 Documentation & Deployment (Tất cả thành viên)

- [ ] 27. Documentation
  - [ ] 27.1 Update service README files
    - Document API endpoints
    - Add setup instructions
    - Add troubleshooting guide
    - _Each member for their service_
  
  - [ ] 27.2 Create API documentation
    - Document request/response formats
    - Add example requests
    - Document error codes
    - _Each member for their service_
  
  - [ ] 27.3 Update main README.md
    - Add deployment instructions
    - Add architecture diagram
    - Add team member responsibilities
    - _Team lead_

- [ ] 28. Deployment preparation
  - [ ] 28.1 Optimize Docker images
    - Use multi-stage builds
    - Minimize image sizes
    - Add health checks
    - _Each member for their service_
  
  - [ ] 28.2 Setup CI/CD pipeline (optional)
    - Configure GitHub Actions
    - Add automated tests
    - Add deployment scripts
    - _DevOps lead_
  
  - [ ] 28.3 Create deployment guide
    - Document production deployment steps
    - Add monitoring setup
    - Add backup procedures
    - _Team lead_

---

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP
- Each task references the responsible team member
- Tasks with "Blocking" dependencies must wait for those tasks to complete
- Use Swagger UI for testing: 
  - Chatbot: http://localhost:8001/docs
  - Query: http://localhost:8002/docs
  - Realtime: http://localhost:8003/docs
- Monitor logs: `docker-compose logs -f [service-name]`
- Checkpoints ensure incremental validation and team sync points

## Integration Points Summary

| From | To | Protocol | Details |
|------|-----|----------|---------|
| Thành viên 4 | Thành viên 5 | Kafka | Topic: `iot_logs` |
| Thành viên 1 | Thành viên 2 | HTTP REST | POST /api/v1/query/execute |
| Thành viên 5 | Thành viên 3 | Redis Pub/Sub | Channel: `iot_events` |
| Thành viên 2 | PostgreSQL | SQL | Read-only (SELECT) |
| Thành viên 5 | PostgreSQL | SQL | Write (INSERT) |
