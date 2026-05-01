#!/usr/bin/env python3
"""
Python test script for Gemini integration
Tests SQL generation and function calling
"""
import requests
import json
import sys
from typing import Dict, Any

BASE_URL = "http://localhost:8001"

# ANSI color codes
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color


class GeminiTester:
    """Test suite for Gemini integration"""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def test_health(self) -> bool:
        """Test service health endpoint"""
        print(f"{BLUE}Testing service health...{NC}")
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                print(f"{GREEN}✓ Service is healthy{NC}")
                return True
            else:
                print(f"{RED}✗ Service returned status {response.status_code}{NC}")
                return False
        except Exception as e:
            print(f"{RED}✗ Cannot connect to service: {e}{NC}")
            return False
    
    def test_chatbot(self, test_name: str, prompt: str, expected_keywords: list = None) -> bool:
        """Test chatbot endpoint with a prompt"""
        print(f"\n{BLUE}Test: {test_name}{NC}")
        print(f"Prompt: {prompt}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/v1/chatbot/chat",
                json={"prompt": prompt},
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"{RED}✗ FAILED - HTTP {response.status_code}{NC}")
                print(f"Response: {response.text[:200]}")
                self.failed += 1
                return False
            
            data = response.json()
            
            # Check if SQL was generated
            if "sql" not in data or not data["sql"]:
                print(f"{RED}✗ FAILED - No SQL generated{NC}")
                self.failed += 1
                return False
            
            sql = data["sql"]
            
            # Validate SQL starts with SELECT
            if not sql.strip().upper().startswith("SELECT"):
                print(f"{RED}✗ FAILED - SQL doesn't start with SELECT{NC}")
                print(f"SQL: {sql}")
                self.failed += 1
                return False
            
            # Check for expected keywords
            if expected_keywords:
                sql_upper = sql.upper()
                missing_keywords = [kw for kw in expected_keywords if kw.upper() not in sql_upper]
                if missing_keywords:
                    print(f"{YELLOW}⚠ WARNING - Missing keywords: {missing_keywords}{NC}")
            
            # Display results
            print(f"{GREEN}✓ PASSED{NC}")
            print(f"SQL: {sql[:100]}...")
            
            if data.get("chart"):
                print(f"Chart Type: {data['chart'].get('type', 'N/A')}")
            
            if data.get("explanation"):
                print(f"Explanation: {data['explanation'][:100]}...")
            
            self.passed += 1
            return True
            
        except requests.exceptions.Timeout:
            print(f"{RED}✗ FAILED - Request timeout{NC}")
            self.failed += 1
            return False
        except Exception as e:
            print(f"{RED}✗ FAILED - {str(e)}{NC}")
            self.failed += 1
            return False
    
    def run_all_tests(self):
        """Run all test cases"""
        print("=" * 50)
        print("Gemini Integration Test Suite")
        print("=" * 50)
        print()
        
        # Check service health
        if not self.test_health():
            print(f"\n{RED}Service is not available. Exiting.{NC}")
            sys.exit(1)
        
        print("\n" + "=" * 50)
        print("Running SQL Generation Tests")
        print("=" * 50)
        
        # Test 1: Simple SELECT
        self.test_chatbot(
            "Simple SELECT Query",
            "Show me all devices",
            expected_keywords=["SELECT", "FROM", "devices"]
        )
        
        # Test 2: Aggregation
        self.test_chatbot(
            "Aggregation Query",
            "What is the average temperature for all sensors?",
            expected_keywords=["SELECT", "AVG", "temperature", "FROM", "logs"]
        )
        
        # Test 3: Time-based query
        self.test_chatbot(
            "Time-based Query",
            "Show me temperature readings from the last 24 hours",
            expected_keywords=["SELECT", "FROM", "logs", "WHERE", "timestamp", "INTERVAL"]
        )
        
        # Test 4: Filtering
        self.test_chatbot(
            "Filtering Query",
            "Show me all active devices",
            expected_keywords=["SELECT", "FROM", "devices", "WHERE", "status"]
        )
        
        # Test 5: GROUP BY
        self.test_chatbot(
            "GROUP BY Query",
            "Count how many logs each device has",
            expected_keywords=["SELECT", "COUNT", "FROM", "logs", "GROUP BY", "device_id"]
        )
        
        # Test 6: Complex aggregation
        self.test_chatbot(
            "Complex Aggregation",
            "Which sensor has the highest average temperature today?",
            expected_keywords=["SELECT", "AVG", "temperature", "GROUP BY", "ORDER BY", "LIMIT"]
        )
        
        # Test 7: JOIN query
        self.test_chatbot(
            "JOIN Query",
            "Show me devices with their latest temperature readings",
            expected_keywords=["SELECT", "FROM", "devices", "JOIN", "logs"]
        )
        
        # Test 8: Date range
        self.test_chatbot(
            "Date Range Query",
            "Show daily statistics for the last 7 days",
            expected_keywords=["SELECT", "FROM", "daily_stats", "WHERE", "date"]
        )
        
        # Test 9: Multiple aggregations
        self.test_chatbot(
            "Multiple Aggregations",
            "Show me min, max, and average temperature for each device",
            expected_keywords=["SELECT", "MIN", "MAX", "AVG", "temperature", "GROUP BY"]
        )
        
        # Test 10: Specific device
        self.test_chatbot(
            "Specific Device Query",
            "Show me all readings from SENSOR_001",
            expected_keywords=["SELECT", "FROM", "logs", "WHERE", "device_id", "SENSOR_001"]
        )
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("Test Summary")
        print("=" * 50)
        total = self.passed + self.failed
        print(f"Total Tests: {total}")
        print(f"{GREEN}Passed: {self.passed}{NC}")
        print(f"{RED}Failed: {self.failed}{NC}")
        
        if self.failed == 0:
            print(f"\n{GREEN}All tests passed! ✓{NC}")
            sys.exit(0)
        else:
            print(f"\n{RED}Some tests failed.{NC}")
            print("\nTroubleshooting steps:")
            print("1. Check Gemini API key in .env file")
            print("2. Verify API key is valid: https://makersuite.google.com/app/apikey")
            print("3. Check service logs: docker-compose logs -f chatbot-service")
            print("4. Ensure Gemini API is enabled in Google Cloud Console")
            sys.exit(1)


def main():
    """Main entry point"""
    tester = GeminiTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()
