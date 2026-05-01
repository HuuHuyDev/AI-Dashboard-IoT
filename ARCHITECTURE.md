# System Architecture - AI-Powered IoT Dashboard

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          AI-Powered IoT Dashboard                        │
│                         Microservices Architecture                       │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                            CLIENT LAYER                                   │
├──────────────────────────────────────────────────────────────────────────┤
│  Web Browser  │  Mobile App  │  IoT Devices  │  External Systems        │
└───────┬──────────────┬──────────────┬────────────────┬───────────────────┘
        │              │              │                │
        │ HTTP/WS      │ HTTP/WS      │ MQTT          │ HTTP
        │              │              │                │
┌───────▼──────────────▼──────────────▼────────────────▼───────────────────┐
│                         API GATEWAY LAYER (Future)                        │
│                    Load Balancer │ Rate Limiter │ Auth                   │
└───────┬──────────────┬──────────────┬────────────────┬───────────────────┘
        │              │              │                │
┌───────▼──────┐ ┌─────▼──────┐ ┌────▼─────────┐ ┌────▼──────────────────┐
│   Chatbot    │ │   Query    │ │  Realtime    │ │    Ingestion          │
│   Service    │ │  Service   │ │  Service     │ │    Service            │
│  (Port 8001) │ │(Port 8002) │ │(Port 8003)   │ │  (Port 8004)          │
│              │ │            │ │              │ │                       │
│ ┌──────────┐ │ │┌──────────┐│ │┌────────────┐│ │ ┌──────────────────┐ │
│ │   LLM    │ │ ││  Cache   ││ ││ WebSocket  ││ │ │  MQTT Consumer   │ │
│ │ Service  │ │ ││ Manager  ││ ││  Manager   ││ │ │                  │ │
│ └──────────┘ │ │└──────────┘│ │└────────────┘│ │ └──────────────────┘ │
│ ┌──────────┐ │ │┌──────────┐│ │┌────────────┐│ │ ┌──────────────────┐ │
│ │  Query   │ │ ││   SQL    ││ ││   Redis    ││ │ │ Kafka Producer   │ │
│ │Orchestr. │ │ ││Validator ││ ││ Subscriber ││ │ │                  │ │
│ └──────────┘ │ │└──────────┘│ │└────────────┘│ │ └──────────────────┘ │
└───────┬──────┘ └─────┬──────┘ └──────┬───────┘ └────────┬──────────────┘
        │              │                │                  │
        │              │                │                  │
        └──────────────┴────────────────┴──────────────────┘
                                │
                    ┌───────────▼────────────┐
                    │  Processing Service    │
                    │    (Port 8005)         │
                    │                        │
                    │ ┌────────────────────┐ │
                    │ │ Kafka Consumer     │ │
                    │ └────────────────────┘ │
                    │ ┌────────────────────┐ │
                    │ │ Data Validator     │ │
                    │ └────────────────────┘ │
                    │ ┌────────────────────┐ │
                    │ │ Data Transformer   │ │
                    │ └────────────────────┘ │
                    │ ┌────────────────────┐ │
                    │ │ Redis Publisher    │ │
                    │ └────────────────────┘ │
                    └───────────┬────────────┘
                                │
┌───────────────────────────────┼────────────────────────────────────────┐
│                        DATA & MESSAGE LAYER                             │
├───────────────────────────────┼────────────────────────────────────────┤
│                               │                                         │
│  ┌─────────────┐   ┌──────────▼──────┐   ┌──────────────┐            │
│  │ PostgreSQL  │   │     Redis       │   │    Kafka     │            │
│  │             │   │                 │   │              │            │
│  │ ┌─────────┐ │   │ ┌─────────────┐ │   │ ┌──────────┐ │            │
│  │ │ devices │ │   │ │Query Cache  │ │   │ │iot_logs  │ │            │
│  │ └─────────┘ │   │ └─────────────┘ │   │ │  topic   │ │            │
│  │ ┌─────────┐ │   │ ┌─────────────┐ │   │ └──────────┘ │            │
│  │ │  logs   │ │   │ │  Pub/Sub    │ │   │              │            │
│  │ └─────────┘ │   │ │new_log_event│ │   │ Zookeeper    │            │
│  │ ┌─────────┐ │   │ └─────────────┘ │   │              │            │
│  │ │daily_   │ │   │                 │   │              │            │
│  │ │ stats   │ │   │                 │   │              │            │
│  │ └─────────┘ │   │                 │   │              │            │
│  │ ┌─────────┐ │   │                 │   │              │            │
│  │ │ alerts  │ │   │                 │   │              │            │
│  │ └─────────┘ │   │                 │   │              │            │
│  └─────────────┘   └─────────────────┘   └──────────────┘            │
│                                                                         │
│  ┌─────────────┐                                                       │
│  │    MQTT     │                                                       │
│  │  Mosquitto  │                                                       │
│  │             │                                                       │
│  │ iot/sensors │                                                       │
│  └─────────────┘                                                       │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL SERVICES                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                      OpenAI GPT-4 API                                   │
│                   (Natural Language Processing)                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Diagrams

### 1. IoT Data Ingestion Flow

```
┌──────────────┐
│ IoT Sensor   │
│ (Temperature,│
│  Humidity,   │
│  Pressure)   │
└──────┬───────┘
       │
       │ MQTT Publish
       │ Topic: iot/sensors/{device_id}
       │ Payload: JSON
       ▼
┌──────────────────┐
│  MQTT Broker     │
│  (Mosquitto)     │
│  Port: 1883      │
└──────┬───────────┘
       │
       │ Subscribe
       ▼
┌──────────────────┐
│ Ingestion Service│
│                  │
│ 1. Receive MQTT  │
│ 2. Parse JSON    │
│ 3. Add metadata  │
└──────┬───────────┘
       │
       │ Kafka Produce
       │ Topic: iot_logs
       │ Key: device_id
       ▼
┌──────────────────┐
│  Kafka Queue     │
│                  │
│ - Partitioned    │
│ - Replicated     │
│ - Durable        │
└──────┬───────────┘
       │
       │ Kafka Consume
       │ Group: processing-service
       ▼
┌──────────────────┐
│Processing Service│
│                  │
│ 1. Validate data │
│ 2. Transform     │
│ 3. Enrich        │
└──────┬───────────┘
       │
       ├─────────────────────┐
       │                     │
       ▼                     ▼
┌──────────────┐      ┌──────────────┐
│ PostgreSQL   │      │    Redis     │
│              │      │              │
│ INSERT INTO  │      │ PUBLISH      │
│ logs         │      │ new_log_event│
│              │      │              │
│ COMMIT       │      │              │
└──────────────┘      └──────┬───────┘
                             │
                             │ Subscribe
                             ▼
                      ┌──────────────┐
                      │  Realtime    │
                      │  Service     │
                      │              │
                      │ Broadcast    │
                      └──────┬───────┘
                             │
                             │ WebSocket
                             ▼
                      ┌──────────────┐
                      │   Clients    │
                      │  (Browser,   │
                      │   Mobile)    │
                      └──────────────┘
```

### 2. AI Query Flow

```
┌──────────────┐
│    User      │
│              │
│ "Show me avg │
│ temperature  │
│ last 24hrs"  │
└──────┬───────┘
       │
       │ HTTP POST /api/v1/chatbot/chat
       │ {"prompt": "..."}
       ▼
┌──────────────────┐
│ Chatbot Service  │
│                  │
│ 1. Receive prompt│
└──────┬───────────┘
       │
       │ OpenAI API Call
       │ Model: GPT-4
       │ Function: generate_sql
       ▼
┌──────────────────┐
│   OpenAI API     │
│                  │
│ 1. Parse prompt  │
│ 2. Understand    │
│    intent        │
│ 3. Generate SQL  │
│ 4. Suggest chart │
└──────┬───────────┘
       │
       │ Function Call Response
       │ {
       │   "sql": "SELECT...",
       │   "chart": {...}
       │ }
       ▼
┌──────────────────┐
│ Chatbot Service  │
│                  │
│ 2. Validate SQL  │
│ 3. Forward query │
└──────┬───────────┘
       │
       │ HTTP POST /api/v1/query/execute
       │ {"sql": "..."}
       ▼
┌──────────────────┐
│  Query Service   │
│                  │
│ 1. Validate SQL  │
│ 2. Generate key  │
└──────┬───────────┘
       │
       │ Check cache
       ▼
┌──────────────────┐
│     Redis        │
│                  │
│ GET query:{hash} │
└──────┬───────────┘
       │
       ├─── Cache Hit ────┐
       │                  │
       │                  ▼
       │           ┌──────────────┐
       │           │Return cached │
       │           │    data      │
       │           └──────┬───────┘
       │                  │
       │ Cache Miss       │
       ▼                  │
┌──────────────────┐      │
│   PostgreSQL     │      │
│                  │      │
│ EXECUTE SQL      │      │
│ FETCH RESULTS    │      │
└──────┬───────────┘      │
       │                  │
       │ Store in cache   │
       ▼                  │
┌──────────────────┐      │
│     Redis        │      │
│                  │      │
│ SET query:{hash} │      │
│ EXPIRE 300       │      │
└──────┬───────────┘      │
       │                  │
       └──────────────────┘
       │
       │ Return results
       ▼
┌──────────────────┐
│  Query Service   │
│                  │
│ Format response  │
└──────┬───────────┘
       │
       │ HTTP Response
       │ {
       │   "data": [...],
       │   "source": "cache/db"
       │ }
       ▼
┌──────────────────┐
│ Chatbot Service  │
│                  │
│ 4. Build response│
│ 5. Add chart cfg │
└──────┬───────────┘
       │
       │ HTTP Response
       │ {
       │   "message": "...",
       │   "sql": "...",
       │   "data": [...],
       │   "chart": {...}
       │ }
       ▼
┌──────────────┐
│    User      │
│              │
│ View results │
│ & chart      │
└──────────────┘
```

### 3. Real-Time Streaming Flow

```
┌──────────────┐
│   Client     │
│  (Browser)   │
└──────┬───────┘
       │
       │ WebSocket Connect
       │ ws://localhost:8003/api/v1/realtime/ws
       ▼
┌──────────────────┐
│ Realtime Service │
│                  │
│ 1. Accept conn   │
│ 2. Add to pool   │
│ 3. Send welcome  │
└──────┬───────────┘
       │
       │ Start heartbeat (30s)
       │
       ├─────────────────────┐
       │                     │
       │ Heartbeat           │ Redis Subscribe
       │ {"type":"heartbeat"}│ Channel: new_log_event
       │                     │
       ▼                     ▼
┌──────────────┐      ┌──────────────┐
│   Client     │      │    Redis     │
│              │      │              │
│ Keep alive   │      │ SUBSCRIBE    │
└──────────────┘      │ new_log_event│
                      └──────┬───────┘
                             │
                             │ New message published
                             │ (from Processing Service)
                             ▼
                      ┌──────────────┐
                      │  Realtime    │
                      │  Service     │
                      │              │
                      │ 1. Receive   │
                      │ 2. Parse     │
                      │ 3. Broadcast │
                      └──────┬───────┘
                             │
                             │ Broadcast to all clients
                             ▼
                      ┌──────────────┐
                      │   Clients    │
                      │              │
                      │ Receive:     │
                      │ {            │
                      │   "type":    │
                      │   "iot_event"│
                      │   "data": {} │
                      │ }            │
                      └──────────────┘
```

## Component Details

### Service Layer

#### Chatbot Service
- **Language**: Python 3.11
- **Framework**: FastAPI
- **Dependencies**: OpenAI SDK, httpx
- **Responsibilities**:
  - Natural language understanding
  - SQL generation via LLM
  - Chart recommendation
  - Query orchestration

#### Query Service
- **Language**: Python 3.11
- **Framework**: FastAPI
- **Dependencies**: SQLAlchemy, Redis
- **Responsibilities**:
  - SQL validation
  - Query execution
  - Result caching
  - Performance optimization

#### Realtime Service
- **Language**: Python 3.11
- **Framework**: FastAPI + WebSocket
- **Dependencies**: Redis (Pub/Sub)
- **Responsibilities**:
  - WebSocket management
  - Real-time broadcasting
  - Connection pooling
  - Event streaming

#### Ingestion Service
- **Language**: Python 3.11
- **Framework**: Async Python
- **Dependencies**: paho-mqtt, kafka-python
- **Responsibilities**:
  - MQTT consumption
  - Message validation
  - Kafka production
  - Protocol translation

#### Processing Service
- **Language**: Python 3.11
- **Framework**: Async Python
- **Dependencies**: kafka-python, SQLAlchemy, Redis
- **Responsibilities**:
  - Message consumption
  - Data validation
  - Data transformation
  - Database persistence
  - Event publishing

### Data Layer

#### PostgreSQL
- **Version**: 15
- **Purpose**: Primary data store
- **Tables**: devices, logs, daily_stats, alerts
- **Features**:
  - ACID compliance
  - JSONB support
  - Full-text search
  - Stored procedures
  - Materialized views

#### Redis
- **Version**: 7
- **Purpose**: Cache + Pub/Sub
- **Data Structures**:
  - Strings (cache)
  - Pub/Sub channels
- **Features**:
  - TTL support
  - Persistence
  - High throughput

#### Kafka
- **Version**: 7.5.0 (Confluent)
- **Purpose**: Message queue
- **Topics**: iot_logs
- **Features**:
  - Partitioning
  - Replication
  - Consumer groups
  - Exactly-once semantics

#### MQTT
- **Implementation**: Eclipse Mosquitto 2.0
- **Purpose**: IoT device communication
- **Features**:
  - Topic-based routing
  - QoS levels
  - Retained messages
  - Wildcard subscriptions

## Scalability Considerations

### Horizontal Scaling

```
┌─────────────────────────────────────────────────────────────┐
│                      Load Balancer                           │
└───────┬─────────────┬─────────────┬─────────────┬───────────┘
        │             │             │             │
┌───────▼──────┐ ┌────▼──────┐ ┌───▼──────┐ ┌────▼──────┐
│ Chatbot-1    │ │Chatbot-2  │ │Query-1   │ │Query-2    │
└──────────────┘ └───────────┘ └──────────┘ └───────────┘

┌───────────────────────────────────────────────────────────┐
│              Kafka (Multiple Partitions)                   │
└───────┬─────────────┬─────────────┬─────────────┬─────────┘
        │             │             │             │
┌───────▼──────┐ ┌────▼──────┐ ┌───▼──────┐ ┌────▼──────┐
│Processing-1  │ │Process-2  │ │Process-3 │ │Process-4  │
│(Partition 0) │ │(Part. 1)  │ │(Part. 2) │ │(Part. 3)  │
└──────────────┘ └───────────┘ └──────────┘ └───────────┘
```

### Database Scaling

```
┌──────────────────────────────────────────────────────────┐
│                  PostgreSQL Primary                       │
│                  (Read + Write)                           │
└───────┬──────────────────────────────────────────────────┘
        │
        │ Replication
        │
        ├─────────────────┬─────────────────┐
        │                 │                 │
┌───────▼──────┐  ┌───────▼──────┐  ┌──────▼───────┐
│  Replica 1   │  │  Replica 2   │  │  Replica 3   │
│  (Read Only) │  │  (Read Only) │  │  (Read Only) │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Cache Scaling

```
┌──────────────────────────────────────────────────────────┐
│                  Redis Cluster                            │
├──────────────────┬──────────────────┬────────────────────┤
│   Master 1       │   Master 2       │   Master 3         │
│   (Slots 0-5460) │ (Slots 5461-     │ (Slots 10923-      │
│                  │  10922)          │  16383)            │
├──────────────────┼──────────────────┼────────────────────┤
│   Replica 1      │   Replica 2      │   Replica 3        │
└──────────────────┴──────────────────┴────────────────────┘
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Security Layers                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Network Layer                                            │
│     - Docker network isolation                               │
│     - Firewall rules                                         │
│     - TLS/SSL (production)                                   │
│                                                              │
│  2. Application Layer                                        │
│     - Input validation (Pydantic)                            │
│     - SQL injection prevention                               │
│     - Rate limiting                                          │
│     - Authentication (JWT - future)                          │
│                                                              │
│  3. Data Layer                                               │
│     - Database user permissions                              │
│     - Redis password                                         │
│     - Encrypted connections                                  │
│     - Data encryption at rest (production)                   │
│                                                              │
│  4. API Layer                                                │
│     - CORS configuration                                     │
│     - API key validation                                     │
│     - Request signing                                        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Monitoring & Observability

```
┌─────────────────────────────────────────────────────────────┐
│                    Observability Stack                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Metrics (Prometheus)                                        │
│  ├─ Service health                                           │
│  ├─ Request rates                                            │
│  ├─ Error rates                                              │
│  ├─ Latency percentiles                                      │
│  └─ Resource usage                                           │
│                                                              │
│  Logs (ELK Stack)                                            │
│  ├─ Application logs                                         │
│  ├─ Access logs                                              │
│  ├─ Error logs                                               │
│  └─ Audit logs                                               │
│                                                              │
│  Traces (Jaeger)                                             │
│  ├─ Request tracing                                          │
│  ├─ Service dependencies                                     │
│  └─ Performance bottlenecks                                  │
│                                                              │
│  Dashboards (Grafana)                                        │
│  ├─ System overview                                          │
│  ├─ Service metrics                                          │
│  ├─ Business metrics                                         │
│  └─ Alerts                                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Deployment Architecture

### Development
```
┌──────────────────────────────────────┐
│      Docker Compose (Single Host)    │
│                                      │
│  All services on one machine         │
│  Shared volumes                      │
│  Development mode                    │
└──────────────────────────────────────┘
```

### Production (Kubernetes)
```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Namespace: iot-dashboard                                    │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Deployments                                           │ │
│  │  ├─ chatbot-service (replicas: 3)                     │ │
│  │  ├─ query-service (replicas: 5)                       │ │
│  │  ├─ realtime-service (replicas: 3)                    │ │
│  │  ├─ ingestion-service (replicas: 2)                   │ │
│  │  └─ processing-service (replicas: 4)                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  StatefulSets                                          │ │
│  │  ├─ postgresql (replicas: 3)                          │ │
│  │  ├─ redis (replicas: 3)                               │ │
│  │  └─ kafka (replicas: 3)                               │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Services                                              │ │
│  │  ├─ LoadBalancer (external)                           │ │
│  │  └─ ClusterIP (internal)                              │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Persistent Volumes                                    │ │
│  │  ├─ postgres-pv (100Gi)                               │ │
│  │  ├─ redis-pv (50Gi)                                   │ │
│  │  └─ kafka-pv (200Gi)                                  │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

This architecture provides:
- **Scalability**: Horizontal scaling of all services
- **Reliability**: Redundancy and fault tolerance
- **Performance**: Caching, connection pooling, async processing
- **Maintainability**: Clear separation of concerns
- **Observability**: Comprehensive monitoring and logging
- **Security**: Multiple layers of protection
