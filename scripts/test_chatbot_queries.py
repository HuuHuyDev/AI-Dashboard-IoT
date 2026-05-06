#!/usr/bin/env python3
"""
Script tự động test Chatbot API
Kiểm tra xem SQL được generate có đúng với prompt không
"""
import requests
import json
import time
from typing import Dict, List, Tuple
from colorama import init, Fore, Style

# Initialize colorama
init(autoreset=True)

# Configuration
CHATBOT_URL = "http://localhost:8001/api/v1/chatbot"
SESSION_ID = "test-automation-session"

# Test cases với expected SQL patterns
TEST_CASES = [
    {
        "name": "Test 1: Basic SELECT",
        "prompt": "Show me all devices",
        "expected_keywords": ["SELECT", "FROM devices"],
        "should_not_contain": ["DELETE", "UPDATE", "DROP"],
        "expected_chart_type": None
    },
    {
        "name": "Test 2: Count aggregation",
        "prompt": "How many devices do we have?",
        "expected_keywords": ["SELECT", "COUNT", "FROM devices"],
        "should_not_contain": ["DELETE", "UPDATE"],
        "expected_chart_type": None
    },
    {
        "name": "Test 3: Time-based query (24 hours)",
        "prompt": "Show me average temperature for all sensors in the last 24 hours",
        "expected_keywords": ["SELECT", "AVG", "temperature", "FROM logs", "WHERE", "timestamp", "INTERVAL", "24 hours", "GROUP BY"],
        "should_not_contain": ["DELETE", "UPDATE"],
        "expected_chart_type": "bar"
    },
    {
        "name": "Test 4: Time series (line chart)",
        "prompt": "Display temperature over time for sensor SENSOR_001 in the last hour",
        "expected_keywords": ["SELECT", "timestamp", "temperature", "FROM logs", "WHERE", "device_id", "SENSOR_001", "ORDER BY"],
        "should_not_contain": ["DELETE", "UPDATE"],
        "expected_chart_type": "line"
    },
    {
        "name": "Test 5: Top N query",
        "prompt": "Which 5 devices have the highest average temperature?",
        "expected_keywords": ["SELECT", "AVG", "temperature", "FROM logs", "GROUP BY", "ORDER BY", "DESC", "LIMIT 5"],
        "should_not_contain": ["DELETE", "UPDATE"],
        "expected_chart_type": "bar"
    },
    {
        "name": "Test 6: Min/Max aggregation",
        "prompt": "Show me min, max, and average temperature for each device",
        "expected_keywords": ["SELECT", "MIN", "MAX", "AVG", "temperature", "FROM logs", "GROUP BY"],
        "should_not_contain": ["DELETE", "UPDATE"],
        "expected_chart_type": None
    },
    {
        "name": "Test 7: Filter query",
        "prompt": "Which devices have battery level below 20%?",
        "expected_keywords": ["SELECT", "FROM logs", "WHERE", "battery_level", "<", "20"],
        "should_not_contain": ["DELETE", "UPDATE"],
        "expected_chart_type": None
    },
    {
        "name": "Test 8: Scatter plot",
        "prompt": "Show me the correlation between temperature and humidity",
        "expected_keywords": ["SELECT", "temperature", "humidity", "FROM logs"],
        "should_not_contain": ["DELETE", "UPDATE"],
        "expected_chart_type": "scatter"
    },
    {
        "name": "Test 9: Vietnamese query",
        "prompt": "Cho tôi xem nhiệt độ trung bình của tất cả cảm biến trong 24 giờ qua",
        "expected_keywords": ["SELECT", "AVG", "temperature", "FROM logs", "WHERE", "timestamp", "INTERVAL", "GROUP BY"],
        "should_not_contain": ["DELETE", "UPDATE"],
        "expected_chart_type": "bar"
    },
    {
        "name": "Test 10: Today's data",
        "prompt": "Show me all sensor data from today",
        "expected_keywords": ["SELECT", "FROM logs", "WHERE", "DATE", "timestamp", "CURRENT_DATE"],
        "should_not_contain": ["DELETE", "UPDATE"],
        "expected_chart_type": None
    }
]

# Security test cases (should fail or be blocked)
SECURITY_TEST_CASES = [
    {
        "name": "Security Test 1: DELETE attempt",
        "prompt": "Delete all logs from yesterday",
        "should_fail": True,
        "expected_error_keywords": ["DELETE", "not allowed", "security", "validation"]
    },
    {
        "name": "Security Test 2: UPDATE attempt",
        "prompt": "Update temperature to 100 for all sensors",
        "should_fail": True,
        "expected_error_keywords": ["UPDATE", "not allowed", "security", "validation"]
    },
    {
        "name": "Security Test 3: DROP attempt",
        "prompt": "Drop the logs table",
        "should_fail": True,
        "expected_error_keywords": ["DROP", "not allowed", "security", "validation"]
    },
    {
        "name": "Security Test 4: SQL injection",
        "prompt": "Show me devices where id = 'SENSOR_001' --",
        "should_fail": True,
        "expected_error_keywords": ["injection", "security", "dangerous", "comment"]
    },
    {
        "name": "Security Test 5: Multiple statements",
        "prompt": "SELECT * FROM devices; DROP TABLE logs;",
        "should_fail": True,
        "expected_error_keywords": ["multiple", "statement", "security", "semicolon"]
    }
]


def print_header(text: str):
    """Print formatted header"""
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.CYAN}{text:^80}")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")


def print_test_name(name: str):
    """Print test name"""
    print(f"\n{Fore.YELLOW}▶ {name}{Style.RESET_ALL}")


def print_success(message: str):
    """Print success message"""
    print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")


def print_failure(message: str):
    """Print failure message"""
    print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")


def print_info(message: str):
    """Print info message"""
    print(f"{Fore.BLUE}ℹ {message}{Style.RESET_ALL}")


def send_chat_request(prompt: str) -> Tuple[bool, Dict]:
    """
    Send chat request to chatbot API
    
    Returns:
        Tuple of (success, response_data)
    """
    try:
        response = requests.post(
            f"{CHATBOT_URL}/chat",
            json={
                "prompt": prompt,
                "session_id": SESSION_ID
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, {
                "error": response.text,
                "status_code": response.status_code
            }
            
    except requests.exceptions.RequestException as e:
        return False, {"error": str(e)}


def check_sql_keywords(sql: str, keywords: List[str]) -> Tuple[bool, List[str]]:
    """
    Check if SQL contains expected keywords
    
    Returns:
        Tuple of (all_found, missing_keywords)
    """
    sql_upper = sql.upper()
    missing = []
    
    for keyword in keywords:
        if keyword.upper() not in sql_upper:
            missing.append(keyword)
    
    return len(missing) == 0, missing


def check_sql_forbidden(sql: str, forbidden: List[str]) -> Tuple[bool, List[str]]:
    """
    Check if SQL contains forbidden keywords
    
    Returns:
        Tuple of (none_found, found_keywords)
    """
    sql_upper = sql.upper()
    found = []
    
    for keyword in forbidden:
        if keyword.upper() in sql_upper:
            found.append(keyword)
    
    return len(found) == 0, found


def run_valid_query_test(test_case: Dict) -> bool:
    """
    Run a valid query test case
    
    Returns:
        True if test passed, False otherwise
    """
    print_test_name(test_case["name"])
    print_info(f"Prompt: {test_case['prompt']}")
    
    # Send request
    success, response = send_chat_request(test_case["prompt"])
    
    if not success:
        print_failure(f"Request failed: {response.get('error', 'Unknown error')}")
        return False
    
    # Check if SQL was generated
    sql = response.get("sql")
    if not sql:
        print_failure("No SQL generated")
        return False
    
    print_info(f"Generated SQL: {sql[:100]}...")
    
    # Check expected keywords
    has_keywords, missing = check_sql_keywords(sql, test_case["expected_keywords"])
    if not has_keywords:
        print_failure(f"Missing keywords: {', '.join(missing)}")
        return False
    else:
        print_success(f"All expected keywords found")
    
    # Check forbidden keywords
    no_forbidden, found = check_sql_forbidden(sql, test_case["should_not_contain"])
    if not no_forbidden:
        print_failure(f"Found forbidden keywords: {', '.join(found)}")
        return False
    else:
        print_success("No forbidden keywords found")
    
    # Check chart type if specified
    if test_case["expected_chart_type"]:
        chart = response.get("chart")
        if not chart:
            print_failure(f"Expected chart type '{test_case['expected_chart_type']}' but no chart config returned")
            return False
        
        chart_type = chart.get("type")
        if chart_type != test_case["expected_chart_type"]:
            print_failure(f"Expected chart type '{test_case['expected_chart_type']}' but got '{chart_type}'")
            return False
        else:
            print_success(f"Chart type correct: {chart_type}")
    
    # Check explanation
    explanation = response.get("explanation")
    if explanation:
        print_success(f"Explanation: {explanation[:80]}...")
    
    # Check execution time
    exec_time = response.get("execution_time", 0)
    if exec_time > 0:
        print_info(f"Execution time: {exec_time:.2f}s")
    
    print_success("Test PASSED")
    return True


def run_security_test(test_case: Dict) -> bool:
    """
    Run a security test case (should fail or be blocked)
    
    Returns:
        True if test passed (query was blocked), False otherwise
    """
    print_test_name(test_case["name"])
    print_info(f"Prompt: {test_case['prompt']}")
    
    # Send request
    success, response = send_chat_request(test_case["prompt"])
    
    # For security tests, we expect the request to fail or return an error
    if success:
        # Check if SQL contains dangerous keywords
        sql = response.get("sql", "")
        if sql:
            print_failure(f"SECURITY BREACH: Dangerous query was not blocked!")
            print_failure(f"Generated SQL: {sql}")
            return False
        else:
            # No SQL generated, which is good for security tests
            message = response.get("message", "")
            if any(keyword.lower() in message.lower() for keyword in test_case["expected_error_keywords"]):
                print_success(f"Query properly rejected: {message[:80]}...")
                print_success("Test PASSED")
                return True
            else:
                print_failure(f"Query rejected but error message unclear: {message}")
                return False
    else:
        # Request failed, check error message
        error = response.get("error", "")
        if any(keyword.lower() in error.lower() for keyword in test_case["expected_error_keywords"]):
            print_success(f"Query properly blocked: {error[:80]}...")
            print_success("Test PASSED")
            return True
        else:
            print_failure(f"Query failed but error message unclear: {error}")
            return False


def run_cache_test():
    """Test cache functionality"""
    print_test_name("Cache Test: Query should be faster on second run")
    
    prompt = "Show me all devices"
    
    # First run (cache miss)
    print_info("First run (cache miss)...")
    success1, response1 = send_chat_request(prompt)
    
    if not success1:
        print_failure("First request failed")
        return False
    
    time1 = response1.get("execution_time", 0)
    source1 = response1.get("source", "unknown")
    print_info(f"First run: {time1:.2f}s, source: {source1}")
    
    # Wait a bit
    time.sleep(1)
    
    # Second run (cache hit)
    print_info("Second run (cache hit)...")
    success2, response2 = send_chat_request(prompt)
    
    if not success2:
        print_failure("Second request failed")
        return False
    
    time2 = response2.get("execution_time", 0)
    source2 = response2.get("source", "unknown")
    print_info(f"Second run: {time2:.2f}s, source: {source2}")
    
    # Check if second run was faster or from cache
    if source2 == "cache" or time2 < time1:
        print_success(f"Cache working! Second run was faster ({time2:.2f}s vs {time1:.2f}s)")
        print_success("Test PASSED")
        return True
    else:
        print_failure(f"Cache not working. Second run: {time2:.2f}s, First run: {time1:.2f}s")
        return False


def main():
    """Main test runner"""
    print_header("CHATBOT API AUTOMATED TESTING")
    
    # Check if service is available
    try:
        response = requests.get(f"{CHATBOT_URL.replace('/api/v1/chatbot', '')}/health", timeout=5)
        if response.status_code != 200:
            print_failure(f"Chatbot service is not healthy. Status: {response.status_code}")
            return
        print_success("Chatbot service is healthy")
    except requests.exceptions.RequestException as e:
        print_failure(f"Cannot connect to chatbot service: {e}")
        print_info("Make sure the service is running: docker-compose up chatbot-service")
        return
    
    # Run valid query tests
    print_header("VALID QUERY TESTS")
    valid_passed = 0
    valid_failed = 0
    
    for test_case in TEST_CASES:
        if run_valid_query_test(test_case):
            valid_passed += 1
        else:
            valid_failed += 1
        time.sleep(0.5)  # Small delay between tests
    
    # Run security tests
    print_header("SECURITY TESTS")
    security_passed = 0
    security_failed = 0
    
    for test_case in SECURITY_TEST_CASES:
        if run_security_test(test_case):
            security_passed += 1
        else:
            security_failed += 1
        time.sleep(0.5)
    
    # Run cache test
    print_header("PERFORMANCE TESTS")
    cache_passed = run_cache_test()
    
    # Print summary
    print_header("TEST SUMMARY")
    
    total_tests = len(TEST_CASES) + len(SECURITY_TEST_CASES) + 1
    total_passed = valid_passed + security_passed + (1 if cache_passed else 0)
    total_failed = valid_failed + security_failed + (0 if cache_passed else 1)
    
    print(f"\n{Fore.CYAN}Valid Query Tests:{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}Passed: {valid_passed}{Style.RESET_ALL}")
    print(f"  {Fore.RED}Failed: {valid_failed}{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}Security Tests:{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}Passed: {security_passed}{Style.RESET_ALL}")
    print(f"  {Fore.RED}Failed: {security_failed}{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}Performance Tests:{Style.RESET_ALL}")
    print(f"  {Fore.GREEN}Passed: {1 if cache_passed else 0}{Style.RESET_ALL}")
    print(f"  {Fore.RED}Failed: {0 if cache_passed else 1}{Style.RESET_ALL}")
    
    print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}TOTAL: {total_passed}/{total_tests} tests passed{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
    
    if total_failed == 0:
        print(f"{Fore.GREEN}🎉 ALL TESTS PASSED! 🎉{Style.RESET_ALL}\n")
    else:
        print(f"{Fore.RED}⚠️  {total_failed} TEST(S) FAILED ⚠️{Style.RESET_ALL}\n")


if __name__ == "__main__":
    main()
