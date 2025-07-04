#!/usr/bin/env python3
"""
Simple Ray cluster test script
"""
import ray
import sys

print("Testing Ray cluster connectivity...")

try:
    print("1. Initializing Ray connection...")
    # Connect to Ray client server (with timeout)
    ray.init(address='ray://localhost:10001', ignore_reinit_error=True)
    
    print("2. Getting cluster information...")
    resources = ray.cluster_resources()
    available = ray.available_resources()
    nodes = ray.nodes()
    
    print(f"   - Total resources: {resources}")
    print(f"   - Available resources: {available}")
    print(f"   - Number of nodes: {len(nodes)}")
    
    print("3. Testing a simple Ray task...")
    @ray.remote
    def test_task():
        return "Task completed successfully!"
    
    future = test_task.remote()
    result = ray.get(future, timeout=10)
    print(f"   - Task result: {result}")
    
    print("4. Shutting down...")
    ray.shutdown()
    
    print("✓ Ray cluster test completed successfully!")

except Exception as e:
    print(f"✗ Ray cluster test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
