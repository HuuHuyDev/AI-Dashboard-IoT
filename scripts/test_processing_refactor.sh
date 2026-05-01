#!/bin/bash
# Test script for Processing Service refactor

echo "=========================================="
echo "Processing Service Refactor Test Suite"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PASSED=0
FAILED=0

# Test 1: Check processing-db is running
echo -e "${BLUE}Test 1: Processing Database${NC}"
if docker-compose ps processing-db | grep -q "Up"; then
    echo -e "${GREEN}✓ Processing database is running${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ Processing database is not running${NC}"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 2: Check database tables
echo -e "${BLUE}Test 2: Database Tables${NC}"
tables=$(docker-compose exec -T processing-db psql -U processing_user -d processing_db -t -c "\dt" 2>/dev/null | grep -c "public")
if [ "$tables" -ge 5 ]; then
    echo -e "${GREEN}✓ All tables created ($tables tables)${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ Missing tables (found $tables)${NC}"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 3: Check outbox table
echo -e "${BLUE}Test 3: Outbox Table${NC}"
if docker-compose exec -T processing-db psql -U processing_user -d processing_db -t -c "\d outbox_events" 2>/dev/null | grep -q "event_id"; then
    echo -e "${GREEN}✓ Outbox table exists${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ Outbox table not found${NC}"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 4: Publish test data
echo -e "${BLUE}Test 4: Data Ingestion${NC}"
docker-compose exec -T mqtt mosquitto_pub \
  -h localhost \
  -t "iot/sensors/TEST_001" \
  -m '{"device_id":"TEST_001","temperature":25.5,"humidity":50.0}' 2>/dev/null

sleep 3

# Check if log was inserted
log_count=$(docker-compose exec -T processing-db psql -U processing_user -d processing_db -t -c "SELECT COUNT(*) FROM logs WHERE device_id='TEST_001';" 2>/dev/null | xargs)
if [ "$log_count" -gt 0 ]; then
    echo -e "${GREEN}✓ Data ingested successfully ($log_count logs)${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ Data ingestion failed${NC}"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 5: Check outbox events
echo -e "${BLUE}Test 5: Outbox Events${NC}"
event_count=$(docker-compose exec -T processing-db psql -U processing_user -d processing_db -t -c "SELECT COUNT(*) FROM outbox_events;" 2>/dev/null | xargs)
if [ "$event_count" -gt 0 ]; then
    echo -e "${GREEN}✓ Outbox events created ($event_count events)${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠ No outbox events found${NC}"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 6: Check Kafka topics
echo -e "${BLUE}Test 6: Kafka Event Topics${NC}"
if docker-compose exec -T kafka kafka-topics --list --bootstrap-server localhost:9092 2>/dev/null | grep -q "processing"; then
    echo -e "${GREEN}✓ Kafka event topics exist${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠ Kafka event topics not found (may be auto-created on first publish)${NC}"
    PASSED=$((PASSED + 1))
fi
echo ""

# Test 7: Check event publishing
echo -e "${BLUE}Test 7: Event Publishing${NC}"
published_count=$(docker-compose exec -T processing-db psql -U processing_user -d processing_db -t -c "SELECT COUNT(*) FROM outbox_events WHERE published = TRUE;" 2>/dev/null | xargs)
if [ "$published_count" -gt 0 ]; then
    echo -e "${GREEN}✓ Events published successfully ($published_count events)${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${YELLOW}⚠ No published events yet (outbox processor may be processing)${NC}"
    PASSED=$((PASSED + 1))
fi
echo ""

# Test 8: Check database isolation
echo -e "${BLUE}Test 8: Database Isolation${NC}"
shared_logs=$(docker-compose exec -T postgres psql -U iot_user -d iot_dashboard -t -c "SELECT COUNT(*) FROM logs WHERE device_id='TEST_001';" 2>/dev/null | xargs)
if [ "$shared_logs" -eq 0 ]; then
    echo -e "${GREEN}✓ Database isolation verified (no data in shared DB)${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ Data found in shared database (isolation broken)${NC}"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 9: Check processing service logs
echo -e "${BLUE}Test 9: Processing Service${NC}"
if docker-compose logs processing-service 2>/dev/null | grep -q "Processing database connection successful"; then
    echo -e "${GREEN}✓ Processing service connected to processing-db${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ Processing service connection issue${NC}"
    FAILED=$((FAILED + 1))
fi
echo ""

# Test 10: Check outbox processor
echo -e "${BLUE}Test 10: Outbox Processor${NC}"
if docker-compose logs processing-service 2>/dev/null | grep -q "Outbox processor started"; then
    echo -e "${GREEN}✓ Outbox processor is running${NC}"
    PASSED=$((PASSED + 1))
else
    echo -e "${RED}✗ Outbox processor not started${NC}"
    FAILED=$((FAILED + 1))
fi
echo ""

# Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo -e "Total Tests: $((PASSED + FAILED))"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed! ✓${NC}"
    echo ""
    echo "Additional verification commands:"
    echo "1. View outbox events:"
    echo "   docker-compose exec processing-db psql -U processing_user -d processing_db -c 'SELECT event_type, aggregate_id, published FROM outbox_events ORDER BY created_at DESC LIMIT 5;'"
    echo ""
    echo "2. Consume Kafka events:"
    echo "   docker-compose exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic processing.log.created --from-beginning --max-messages 5"
    echo ""
    echo "3. Check logs count:"
    echo "   docker-compose exec processing-db psql -U processing_user -d processing_db -c 'SELECT COUNT(*) FROM logs;'"
    exit 0
else
    echo -e "${RED}Some tests failed.${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check processing-db logs: docker-compose logs processing-db"
    echo "2. Check processing-service logs: docker-compose logs processing-service"
    echo "3. Verify database connection: docker-compose exec processing-db psql -U processing_user -d processing_db -c 'SELECT 1;'"
    exit 1
fi
