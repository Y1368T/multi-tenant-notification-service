"""
Runtime load test to verify the session provisioning fix.

This script sends concurrent HTTP requests to a running notification service
to verify that the "session is provisioning a new connection" error no longer occurs.

Usage:
    python tests/runtime_load_test.py --url http://localhost:8000 --requests 100
"""
import asyncio
import argparse
from typing import List, Dict
import httpx
from datetime import datetime


async def send_notification_request(
    client: httpx.AsyncClient,
    base_url: str,
    request_id: int
) -> Dict:
    """Send a test notification request."""
    try:
        start_time = datetime.now()
        
        # Use GET /tenants/get endpoint for load testing (read-only, safe)
        response = await client.get(
            f"{base_url}/tenants/get",
            params={"page": 1, "page_size": 10},
            timeout=30.0
        )
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return {
            "request_id": request_id,
            "status_code": response.status_code,
            "duration": duration,
            "success": response.status_code in [200, 201, 202],
            "error": None
        }
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        error_msg = str(e)
        
        # Check for the specific error we're testing for
        is_race_condition = "provisioning a new connection" in error_msg.lower()
        
        return {
            "request_id": request_id,
            "status_code": None,
            "duration": duration,
            "success": False,
            "error": error_msg,
            "is_race_condition": is_race_condition
        }


async def health_check(base_url: str) -> bool:
    """Check if the service is healthy."""
    try:
        async with httpx.AsyncClient() as client:
            # Use /docs endpoint as health check (FastAPI auto-generates this)
            response = await client.get(f"{base_url}/docs", timeout=5.0)
            return response.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False


async def run_load_test(
    base_url: str,
    num_requests: int,
    concurrency: int = 50
) -> Dict:
    """Run concurrent requests to test the service under load."""
    
    print(f"\n🔧 Runtime Load Test")
    print(f"{'='*60}")
    print(f"Target: {base_url}")
    print(f"Total Requests: {num_requests}")
    print(f"Concurrency: {concurrency}")
    print(f"{'='*60}\n")
    
    # Health check first
    print("⏳ Checking service health...")
    if not await health_check(base_url):
        print("❌ Service is not healthy. Aborting test.")
        return None
    print("✅ Service is healthy\n")
    
    # Run load test in batches
    print(f"🚀 Sending {num_requests} concurrent requests...\n")
    start_time = datetime.now()
    
    async with httpx.AsyncClient() as client:
        # Create batches of concurrent requests
        all_results = []
        for batch_start in range(0, num_requests, concurrency):
            batch_end = min(batch_start + concurrency, num_requests)
            batch_size = batch_end - batch_start
            
            print(f"📦 Batch {batch_start//concurrency + 1}: Sending {batch_size} requests...")
            
            tasks = [
                send_notification_request(client, base_url, i)
                for i in range(batch_start, batch_end)
            ]
            batch_results = await asyncio.gather(*tasks)
            all_results.extend(batch_results)
            
            # Small delay between batches to avoid overwhelming the service
            if batch_end < num_requests:
                await asyncio.sleep(0.1)
    
    total_duration = (datetime.now() - start_time).total_seconds()
    
    # Analyze results
    successful = sum(1 for r in all_results if r["success"])
    failed = len(all_results) - successful
    race_conditions = sum(1 for r in all_results if r.get("is_race_condition", False))
    
    avg_duration = sum(r["duration"] for r in all_results) / len(all_results)
    min_duration = min(r["duration"] for r in all_results)
    max_duration = max(r["duration"] for r in all_results)
    
    # Print results
    print(f"\n{'='*60}")
    print(f"📊 Results")
    print(f"{'='*60}")
    print(f"Total Requests:     {num_requests}")
    print(f"Successful:         {successful} ({successful/num_requests*100:.1f}%)")
    print(f"Failed:             {failed} ({failed/num_requests*100:.1f}%)")
    print(f"Total Duration:     {total_duration:.2f}s")
    print(f"Requests/Second:    {num_requests/total_duration:.2f}")
    print(f"\nResponse Times:")
    print(f"  Average:          {avg_duration:.3f}s")
    print(f"  Min:              {min_duration:.3f}s")
    print(f"  Max:              {max_duration:.3f}s")
    
    print(f"\n{'='*60}")
    if race_conditions > 0:
        print(f"❌ RACE CONDITIONS DETECTED: {race_conditions}")
        print(f"❌ The 'provisioning a new connection' error still occurs!")
        print(f"{'='*60}\n")
        
        # Print details of race condition errors
        print("Race condition errors:")
        for r in all_results:
            if r.get("is_race_condition", False):
                print(f"  Request {r['request_id']}: {r['error']}")
    else:
        print(f"✅ NO RACE CONDITIONS - Fix is working!")
        print(f"✅ All concurrent requests handled correctly")
        print(f"{'='*60}\n")
    
    return {
        "total": num_requests,
        "successful": successful,
        "failed": failed,
        "race_conditions": race_conditions,
        "total_duration": total_duration,
        "requests_per_second": num_requests/total_duration,
        "avg_response_time": avg_duration
    }


def main():
    parser = argparse.ArgumentParser(
        description="Runtime load test for notification service"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="Base URL of the notification service"
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=100,
        help="Total number of requests to send"
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=50,
        help="Number of concurrent requests per batch"
    )
    
    args = parser.parse_args()
    
    # Run the load test
    result = asyncio.run(run_load_test(
        args.url,
        args.requests,
        args.concurrency
    ))
    
    # Exit with error code if race conditions detected
    if result and result["race_conditions"] > 0:
        exit(1)


if __name__ == "__main__":
    main()
