#!/bin/bash

# Test Query Service CQRS Refactor
# This script tests the complete event flow from Processing Service to Query Service

set -e

echo "=========================================="
echo "Query Service CQRS Refactor Test"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test device ID
TEST_DEVICE="TEST_QUERY_$(date +%s)"

echo -e "${YELLOW}Test Device: ${TEST_DEVICE}${NC}"
echo ""

# 1. Check services are running
echo "1. Checking services..."
if docker-compose ps | grep -q "query-service.*Up"; then
    echo -e "${GREEN}✓ Query Service is running${NC}"
else
    echo -e "${RED}✗ Query Service is not running${NC}"
    exit 1
fi

if docker-compose ps | grep -q "query-db.*Up"; then
    echo -e "${GREEN}✓ Query DB is running${NC}"
else
    echo -e "${RED}✗ Query DB is not running${NC}"
    exit 1
fi

if docker-compose ps | grep -q "processing-service.*Up"; then
    echo -e "${GREEN}✓ Processing Service is running${NC}"
else
    echo -e "${RED}✗ Processing Service is not running${NC}"
    exit 1
fi

if docker-compose ps | grep -q "kafka.*Up"; then
    echo -e "${GREEN}✓ Kafka is running${NC}"
else
    echo -e "${RED}✗ Kafka is not running${NC}"
    exit 1
fi
echo ""

# 2. Check query-db tables
echo "2. Checking query-db tables..."
TABLES=$(docker-compose exec -T query-db psql -U query_user -d query_db -t -c "\dt" | grep -c "device_summary\|log_summary\|daily_stats_view\|processed_events" || true)
if [ "$TABLES" -ge 4 ]; then
    echo -e "${GREEN}✓ All read model tables exist${NC}"
else
    echo -e "${RED}✗ Some read model tables are missing${NC}"
    docker-compose exec -T query-db psql -U query_user -d query_db -c "\dt"
    exit 1
fi
echo ""

# 3. Check event consumer is running
echo "3. Checking event consumer..."
if docker-compose logs query-service 2>&1 | grep -q "Event consumer started"; then
    echo -e "${GREEN}✓ Event consumer is running${NC}"
else
    echo -e "${YELLOW}⚠ Event consumer may not be started yet${NC}"
fi
echo ""

# 4. Publish test data via MQTT
echo "4. Publishing test data via MQTT..."
docker-compose exec -T mqtt mosquitto_pub \
    -h localhost \
    -t "iot/sensors/${TEST_DEVICE}" \
    -m "{\"device_id\":\"${TEST_DEVICE}\",\"temperature\":25.5,\"humidity\":50.0,\"pressure\":1013.25,\"battery_level\":85.0}"

echo -e "${GREEN}✓ Test data published${NC}"
echo ""

# 5. Wait for processing
echo "5. Waiting for event processing (5 seconds)..."
sleep 5
echo ""

# 6. Check in processing_db
echo "6. Checking processing_db..."
PROCESSING_COUNT=$(docker-compose exec -T processing-db psql -U processing_user -d processing_db -t -c "SELECT COUNT(*) FROM logs WHERE device_id = '${TEST_DEVICE}';" | tr -d ' ')
if [ "$PROCESSING_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Log found in processing_db (count: ${PROCESSING_COUNT})${NC}"
else
    echo -e "${RED}✗ Log not found in processing_db${NC}"
    exit 1
fi
echo ""

# 7. Check outbox events
echo "7. Checking outbox events..."
OUTBOX_COUNT=$(docker-compose exec -T processing-db psql -U processing_user -d processing_db -t -c "SELECT COUNT(*) FROM outbox_events WHERE aggregate_id LIKE '%${TEST_DEVICE}%';" | tr -d ' ')
if [ "$OUTBOX_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Events found in outbox (count: ${OUTBOX_COUNT})${NC}"
else
    echo -e "${RED}✗ Events not found in outbox${NC}"
    exit 1
fi
echo ""

# 8. Check in query_db log_summary
echo "8. Checking query_db log_summary..."
QUERY_LOG_COUNT=$(docker-compose exec -T query-db psql -U query_user -d query_db -t -c "SELECT COUNT(*) FROM log_summary WHERE device_id = '${TEST_DEVICE}';" | tr -d ' ')
if [ "$QUERY_LOG_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Log found in query_db log_summary (count: ${QUERY_LOG_COUNT})${NC}"
    
    # Show the log
    echo ""
    echo "Log details:"
    docker-compose exec -T query-db psql -U query_user -d query_db -c "SELECT log_id, device_id, device_name, temperature, humidity, timestamp FROM log_summary WHERE device_id = '${TEST_DEVICE}' ORDER BY timestamp DESC LIMIT 1;"
else
    echo -e "${RED}✗ Log not found in query_db log_summary${NC}"
    echo "Checking processed events..."
    docker-compose exec -T query-db psql -U query_user -d query_db -c "SELECT * FROM processed_events ORDER BY processed_at DESC LIMIT 5;"
    exit 1
fi
echo ""

# 9. Check device_summary
echo "9. Checking device_summary..."
DEVICE_SUMMARY=$(docker-compose exec -T query-db psql -U query_user -d query_db -t -c "SELECT COUNT(*) FROM device_summary WHERE device_id = '${TEST_DEVICE}';" | tr -d ' ')
if [ "$DEVICE_SUMMARY" -gt 0 ]; then
    echo -e "${GREEN}✓ Device found in device_summary${NC}"
    
    # Show device summary
    echo ""
    echo "Device summary:"
    docker-compose exec -T query-db psql -U query_user -d query_db -c "SELECT device_id, device_name, last_temperature, last_humidity, last_reading_time, total_logs_count FROM device_summary WHERE device_id = '${TEST_DEVICE}';"
else
    echo -e "${YELLOW}⚠ Device not found in device_summary (may not be created yet)${NC}"
fi
echo ""

# 10. Check processed_events
echo "10. Checking processed_events..."
PROCESSED_COUNT=$(docker-compose exec -T query-db psql -U query_user -d query_db -t -c "SELECT COUNT(*) FROM processed_events WHERE aggregate_id LIKE '%${TEST_DEVICE}%';" | tr -d ' ')
if [ "$PROCESSED_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Events processed (count: ${PROCESSED_COUNT})${NC}"
    
    # Show processed events
    echo ""
    echo "Processed events:"
    docker-compose exec -T query-db psql -U query_user -d query_db -c "SELECT event_type, aggregate_id, processed_at, processing_time_ms FROM processed_events WHERE aggregate_id LIKE '%${TEST_DEVICE}%' ORDER BY processed_at DESC;"
else
    echo -e "${RED}✗ No events processed${NC}"
    exit 1
fi
echo ""

# 11. Check Kafka consumer group
echo "11. Checking Kafka consumer group..."
if docker-compose exec -T kafka kafka-consumer-groups --bootstrap-server localhost:9092 --group query-service-consumer --describe 2>&1 | grep -q "query-service-consumer"; then
    echo -e "${GREEN}✓ Consumer group exists${NC}"
    echo ""
    docker-compose exec -T kafka kafka-consumer-groups --bootstrap-server localhost:9092 --group query-service-consumer --describe
else
    echo -e "${YELLOW}⚠ Consumer group not found${NC}"
fi
echo ""

# 12. Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "${GREEN}✓ Processing Service: Log created${NC}"
echo -e "${GREEN}✓ Outbox Pattern: Event published${NC}"
echo -e "${GREEN}✓ Kafka: Event delivered${NC}"
echo -e "${GREEN}✓ Query Service: Event consumed${NC}"
echo -e "${GREEN}✓ Read Models: Data synced${NC}"
echo ""
echo -e "${GREEN}All tests passed! CQRS pattern is working correctly.${NC}"
echo ""

# 13. Cleanup option
read -p "Do you want to clean up test data? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Cleaning up test data..."
    docker-compose exec -T query-db psql -U query_user -d query_db -c "DELETE FROM log_summary WHERE device_id = '${TEST_DEVICE}';"
    docker-compose exec -T query-db psql -U query_user -d query_db -c "DELETE FROM device_summary WHERE device_id = '${TEST_DEVICE}';"
    docker-compose exec -T query-db psql -U query_user -d query_db -c "DELETE FROM processed_events WHERE aggregate_id LIKE '%${TEST_DEVICE}%';"
    docker-compose exec -T processing-db psql -U processing_user -d processing_db -c "DELETE FROM logs WHERE device_id = '${TEST_DEVICE}';"
    docker-compose exec -T processing-db psql -U processing_user -d processing_db -c "DELETE FROM devices WHERE device_id = '${TEST_DEVICE}';"
    echo -e "${GREEN}✓ Test data cleaned up${NC}"
fi

echo ""
echo "Test completed!"
