#!/usr/bin/env python3
"""
Compare performance between OpenAI and Gemini
Useful for benchmarking after migration
"""
import time
import requests
import json
from typing import Dict, List
import statistics

BASE_URL = "http://localhost:8001"

# Test queries
TEST_QUERIES = [
    "Show me all devices",
    "What is the average temperature for all sensors?",
    "Show me temperature readings from the last 24 hours",
    "Which sensor has the highest average temperature today?",
    "Count how many logs each device has",
]


def test_query(prompt: str) -> Dict:
    """Test a single query and measure performance"""
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/chatbot/chat",
            json={"prompt": prompt},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        end_time = time.time()
        latency = end_time - start_time
        
        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "latency": latency,
                "sql_generated": bool(data.get("sql")),
                "chart_generated": bool(data.get("chart")),
                "source": data.get("source", "unknown")
            }
        else:
            return {
                "success": False,
                "latency": latency,
                "error": f"HTTP {response.status_code}"
            }
    except Exception as e:
        end_time = time.time()
        return {
            "success": False,
            "latency": end_time - start_time,
            "error": str(e)
        }


def run_benchmark(num_iterations: int = 3):
    """Run benchmark tests"""
    print("=" * 60)
    print("LLM Performance Benchmark")
    print("=" * 60)
    print(f"\nRunning {num_iterations} iterations for each query...")
    print()
    
    results = []
    
    for query in TEST_QUERIES:
        print(f"\nTesting: {query}")
        query_results = []
        
        for i in range(num_iterations):
            print(f"  Iteration {i+1}/{num_iterations}...", end=" ")
            result = test_query(query)
            query_results.append(result)
            
            if result["success"]:
                print(f"✓ {result['latency']:.2f}s")
            else:
                print(f"✗ {result.get('error', 'Unknown error')}")
        
        # Calculate statistics
        latencies = [r["latency"] for r in query_results if r["success"]]
        success_rate = sum(1 for r in query_results if r["success"]) / len(query_results) * 100
        
        if latencies:
            results.append({
                "query": query,
                "success_rate": success_rate,
                "avg_latency": statistics.mean(latencies),
                "min_latency": min(latencies),
                "max_latency": max(latencies),
                "std_dev": statistics.stdev(latencies) if len(latencies) > 1 else 0
            })
    
    # Print summary
    print("\n" + "=" * 60)
    print("Performance Summary")
    print("=" * 60)
    
    if results:
        all_latencies = [r["avg_latency"] for r in results]
        all_success_rates = [r["success_rate"] for r in results]
        
        print(f"\nOverall Statistics:")
        print(f"  Average Latency: {statistics.mean(all_latencies):.2f}s")
        print(f"  Min Latency: {min(all_latencies):.2f}s")
        print(f"  Max Latency: {max(all_latencies):.2f}s")
        print(f"  Success Rate: {statistics.mean(all_success_rates):.1f}%")
        
        print(f"\nDetailed Results:")
        print(f"{'Query':<50} {'Avg (s)':<10} {'Min (s)':<10} {'Max (s)':<10} {'Success':<10}")
        print("-" * 90)
        
        for r in results:
            print(f"{r['query'][:47]:<50} {r['avg_latency']:<10.2f} {r['min_latency']:<10.2f} {r['max_latency']:<10.2f} {r['success_rate']:<10.1f}%")
        
        # Performance rating
        avg_latency = statistics.mean(all_latencies)
        avg_success = statistics.mean(all_success_rates)
        
        print("\n" + "=" * 60)
        print("Performance Rating")
        print("=" * 60)
        
        if avg_latency < 2.0 and avg_success > 95:
            print("✓ EXCELLENT - Fast and reliable")
        elif avg_latency < 3.0 and avg_success > 90:
            print("✓ GOOD - Acceptable performance")
        elif avg_latency < 5.0 and avg_success > 80:
            print("⚠ FAIR - Could be improved")
        else:
            print("✗ POOR - Needs optimization")
        
        print(f"\nLatency: {avg_latency:.2f}s (Target: <3.0s)")
        print(f"Success Rate: {avg_success:.1f}% (Target: >95%)")
    else:
        print("\n✗ No successful results to analyze")


if __name__ == "__main__":
    import sys
    
    iterations = 3
    if len(sys.argv) > 1:
        try:
            iterations = int(sys.argv[1])
        except ValueError:
            print("Usage: python compare_llm_performance.py [iterations]")
            sys.exit(1)
    
    run_benchmark(iterations)
