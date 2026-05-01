#!/bin/bash
# System Verification Script
# Checks if all services are running and healthy

echo "=========================================="
echo "AI-Powered IoT Dashboard - System Verification"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check service health
check_service() {
    local service_name=$1
    local port=$2
    local endpoint=$3
    
    echo -n "Checking $service_name (port $port)... "
    
    response=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port$endpoint 2>/dev/null)
    
    if [ "$response" = "200" ]; then
        echo -e "${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "${RED}✗ Unhealthy (HTTP $response)${NC}"
        return 1
    fi
}

# Function to check Docker container
check_container() {
    local container_name=$1
    
    echo -n "Checking container $container_name... "
    
    status=$(docker ps --filter "name=$container_name" --format "{{.Status}}" 2>/dev/null)
    
    if [[ $status == *"Up"* ]]; then
        echo -e "${GREEN}✓ Running${NC}"
        return 0
    else
        echo -e "${RED}✗ Not running${NC}"
        return 1
    fi
}

# Check if Docker is running
echo "1. Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker is not running${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"
echo ""

# Check containers
echo "2. Checking Docker Containers..."
check_container "iot-postgres"
check_container "iot-redis"
check_container "iot-kafka"
check_container "iot-zookeeper"
check_container "iot-mqtt"
check_container "chatbot-service"
check_container "query-service"
check_container "realtime-service"
check_container "ingestion-service"
check_container "processing-service"
echo ""

# Check service health endpoints
echo "3. Checking Service Health Endpoints..."
check_service "Chatbot Service" 8001 "/health"
check_service "Query Service" 8002 "/health"
check_service "Realtime Service" 8003 "/health"
echo ""

# Check PostgreSQL
echo "4. Checking PostgreSQL..."
echo -n "Checking database connection... "
if docker exec iot-postgres psql -U iot_user -d iot_dashboard -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Connected${NC}"
    
    echo -n "Checking devices table... "
    device_count=$(docker exec iot-postgres psql -U iot_user -d iot_dashboard -t -c "SELECT COUNT(*) FROM devices;" 2>/dev/null | xargs)
    echo -e "${GREEN}✓ $device_count devices${NC}"
    
    echo -n "Checking logs table... "
    log_count=$(docker exec iot-postgres psql -U iot_user -d iot_dashboard -t -c "SELECT COUNT(*) FROM logs;" 2>/dev/null | xargs)
    echo -e "${GREEN}✓ $log_count logs${NC}"
else
    echo -e "${RED}✗ Connection failed${NC}"
fi
echo ""

# Check Redis
echo "5. Checking Redis..."
echo -n "Checking Redis connection... "
if docker exec iot-redis redis-cli -a redis_password_2024 PING 2>/dev/null | grep -q "PONG"; then
    echo -e "${GREEN}✓ Connected${NC}"
else
    echo -e "${RED}✗ Connection failed${NC}"
fi
echo ""

# Check Kafka
echo "6. Checking Kafka..."
echo -n "Checking Kafka topics... "
topics=$(docker exec iot-kafka kafka-topics --list --bootstrap-server localhost:9092 2>/dev/null | grep -c "iot_logs")
if [ "$topics" -ge 1 ]; then
    echo -e "${GREEN}✓ Topic 'iot_logs' exists${NC}"
else
    echo -e "${YELLOW}⚠ Topic 'iot_logs' not found (will be auto-created)${NC}"
fi
echo ""

# Test Query Service
echo "7. Testing Query Service..."
echo -n "Executing test query... "
response=$(curl -s -X POST http://localhost:8002/api/v1/query/execute \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT COUNT(*) as count FROM devices"}' 2>/dev/null)

if echo "$response" | grep -q "data"; then
    echo -e "${GREEN}✓ Query executed successfully${NC}"
    echo "   Response: $(echo $response | head -c 100)..."
else
    echo -e "${RED}✗ Query failed${NC}"
fi
echo ""

# Test Chatbot Service (if OpenAI key is configured)
echo "8. Testing Chatbot Service..."
echo -n "Checking OpenAI configuration... "
response=$(curl -s -X POST http://localhost:8001/api/v1/chatbot/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Show me all devices"}' 2>/dev/null)

if echo "$response" | grep -q "sql"; then
    echo -e "${GREEN}✓ Chatbot is working${NC}"
elif echo "$response" | grep -q "API key"; then
    echo -e "${YELLOW}⚠ OpenAI API key not configured${NC}"
else
    echo -e "${RED}✗ Chatbot service error${NC}"
fi
echo ""

# Summary
echo "=========================================="
echo "Verification Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. If all checks passed, your system is ready!"
echo "2. If OpenAI key warning, edit .env and add your API key"
echo "3. To stream test data: docker-compose exec processing-service python /app/../scripts/stream_from_csv.py --generate --duration 60"
echo "4. To view logs: docker-compose logs -f [service-name]"
echo ""
echo "For more information, see README.md and QUICKSTART.md"
