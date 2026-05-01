#!/bin/bash

echo "========================================="
echo "Microservices E2E Test"
echo "========================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test results
PASSED=0
FAILED=0

test_service() {
    SERVICE=$1
    URL=$2
    
    echo -n "Testing $SERVICE... "
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" $URL)
    
    if [ "$RESPONSE" = "200" ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAILED (HTTP $RESPONSE)${NC}"
        ((FAILED++))
    fi
}

echo ""
echo "1. Health Checks"
echo "-----------------"
test_service "Chatbot Service" "http://localhost:8001/health"
test_service "Query Service" "http://localhost:8002/health"
test_service "Realtime Service" "http://localhost:8003/health"
test_service "Processing Service" "http://localhost:8005/health"

echo ""
echo "2. Redis Instances"
echo "------------------"
for PORT in 6379 6380 6381 6382; do
    echo -n "Testing Redis on port $PORT... "
    if redis-cli -p $PORT ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((FAILED++))
    fi
done

echo ""
echo "3. MQTT → Kafka Flow"
echo "--------------------"
echo -n "Publishing test message to MQTT... "
mosquitto_pub -h localhost -t "iot/sensors/test" -m '{"device_id":"test001","temperature":25.5,"humidity":60,"timestamp":"2024-01-01T00:00:00Z"}' > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${RED}✗ FAILED${NC}"
    ((FAILED++))
fi

echo ""
echo "4. Query Service Data"
echo "---------------------"
sleep 2  # Wait for processing
test_service "Get Devices" "http://localhost:8002/api/v1/query/devices"
test_service "Get Logs" "http://localhost:8002/api/v1/query/logs"

echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo "========================================="

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
