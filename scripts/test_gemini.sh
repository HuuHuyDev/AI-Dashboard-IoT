#!/bin/bash
# Test script for Gemini integration in Chatbot Service

echo "=========================================="
echo "Gemini Integration Test Suite"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8001"
PASSED=0
FAILED=0

# Function to test endpoint
test_endpoint() {
    local test_name=$1
    local prompt=$2
    
    echo -e "${BLUE}Test: $test_name${NC}"
    echo "Prompt: $prompt"
    
    response=$(curl -s -X POST $BASE_URL/api/v1/chatbot/chat \
        -H "Content-Type: application/json" \
        -d "{\"prompt\": \"$prompt\"}" 2>&1)
    
    # Check if response contains SQL
    if echo "$response" | grep -q '"sql"'; then
        echo -e "${GREEN}✓ PASSED${NC}"
        echo "SQL Generated: $(echo $response | jq -r '.sql' 2>/dev/null | head -c 100)..."
        echo "Chart Type: $(echo $response | jq -r '.chart.type' 2>/dev/null)"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}✗ FAILED${NC}"
        echo "Response: $(echo $response | head -c 200)"
        FAILED=$((FAILED + 1))
    fi
    echo ""
}

# Check if service is running
echo "1. Checking if Chatbot Service is running..."
health_response=$(curl -s $BASE_URL/health 2>&1)

if echo "$health_response" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Service is running${NC}"
else
    echo -e "${RED}✗ Service is not running${NC}"
    echo "Please start the service with: docker-compose up -d chatbot-service"
    exit 1
fi
echo ""

# Check Gemini configuration
echo "2. Checking Gemini configuration..."
if docker-compose logs chatbot-service 2>/dev/null | grep -q "Google Gemini API configured: True"; then
    echo -e "${GREEN}✓ Gemini API is configured${NC}"
else
    echo -e "${YELLOW}⚠ Cannot verify Gemini configuration from logs${NC}"
fi
echo ""

# Run tests
echo "3. Running Gemini SQL Generation Tests..."
echo ""

# Test 1: Simple SELECT
test_endpoint "Simple SELECT Query" "Show me all devices"

# Test 2: Aggregation
test_endpoint "Aggregation Query" "What is the average temperature for all sensors?"

# Test 3: Time-based query
test_endpoint "Time-based Query" "Show me temperature readings from the last 24 hours"

# Test 4: Filtering
test_endpoint "Filtering Query" "Show me all active devices"

# Test 5: JOIN query
test_endpoint "JOIN Query" "Show me devices with their latest temperature readings"

# Test 6: GROUP BY
test_endpoint "GROUP BY Query" "Count how many logs each device has"

# Test 7: Complex aggregation
test_endpoint "Complex Aggregation" "Which sensor has the highest average temperature today?"

# Test 8: Date range
test_endpoint "Date Range Query" "Show daily statistics for the last 7 days"

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
    exit 0
else
    echo -e "${RED}Some tests failed. Please check the logs.${NC}"
    echo ""
    echo "Troubleshooting steps:"
    echo "1. Check Gemini API key: docker-compose logs chatbot-service | grep GEMINI"
    echo "2. Verify API key is valid: https://makersuite.google.com/app/apikey"
    echo "3. Check service logs: docker-compose logs -f chatbot-service"
    exit 1
fi
