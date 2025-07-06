#!/usr/bin/env python3
"""
Test script to verify Ray watcher functionality
"""
import os
import sys
import time
import ray

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

def test_ray_connection():
    """Test connecting to Ray cluster."""
    print("Testing Ray connection...")
    
    try:
        # Try to connect to Ray cluster
        ray.init(address="ray://ray-address:10001")
        print("✓ Successfully connected to Ray cluster")
        
        # Get cluster info
        cluster_resources = ray.cluster_resources()
        available_resources = ray.available_resources()
        
        print(f"Cluster resources: {cluster_resources}")
        print(f"Available resources: {available_resources}")
        
        # Shutdown connection
        ray.shutdown()
        return True
        
    except Exception as e:
        print(f"✗ Failed to connect to Ray cluster: {e}")
        return False

def test_watcher_import():
    """Test importing the watcher module."""
    print("\nTesting watcher module import...")
    
    try:
        import ray_watcher
        print("✓ Successfully imported ray_watcher module")
        
        # Test key functions exist
        functions = ['initialize_ray_connection', 'get_cluster_metrics', 'should_scale_up', 'scale_up_worker']
        for func in functions:
            if hasattr(ray_watcher, func):
                print(f"✓ Function {func} exists")
            else:
                print(f"✗ Function {func} missing")
                return False
                
        return True
        
    except Exception as e:
        print(f"✗ Failed to import ray_watcher: {e}")
        return False

def test_watcher_initialization():
    """Test watcher initialization."""
    print("\nTesting watcher initialization...")
    
    try:
        # Set test environment variables
        os.environ['RAY_HEAD_ADDRESS'] = 'localhost:10001'
        
        import ray_watcher
        result = ray_watcher.initialize_ray_connection()
        
        if result:
            print("✓ Watcher can initialize Ray connection")
            
            # Test getting metrics
            metrics = ray_watcher.get_cluster_metrics()
            if metrics:
                print(f"✓ Successfully got cluster metrics: {metrics}")
            else:
                print("✗ Failed to get cluster metrics")
                return False
            
            # Cleanup
            if ray.is_initialized():
                ray.shutdown()
                
            return True
        else:
            print("✗ Failed to initialize Ray connection")
            return False
            
    except Exception as e:
        print(f"✗ Error during watcher initialization test: {e}")
        return False

def main():
    """Run all tests."""
    print("=== Ray Watcher Test Suite ===")
    
    tests = [
        ("Ray Connection", test_ray_connection),
        ("Watcher Import", test_watcher_import),
        ("Watcher Initialization", test_watcher_initialization),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n--- Running {test_name} Test ---")
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Error in {test_name} test: {e}")
            failed += 1
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
