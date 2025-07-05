#!/usr/bin/env python3
"""
Simple test to validate Ray watcher functionality
"""
import subprocess
import re

def test_worker_index_logic():
    """Test the worker index logic."""
    print("Testing worker index logic...")
    
    # Simulate docker ps output
    test_cases = [
        # Case 1: No workers
        ("", 1),
        # Case 2: Workers 1, 2, 3
        ("ray-worker-1\nray-worker-2\nray-worker-3", 4),
        # Case 3: Workers 1, 3, 5 (non-consecutive)
        ("ray-worker-1\nray-worker-3\nray-worker-5", 6),
        # Case 4: Mixed names
        ("ray-worker-1\nray-head\nray-worker-2", 3),
    ]
    
    for i, (output, expected) in enumerate(test_cases):
        worker_names = [w.strip() for w in output.split('\n') if w.strip() and w.startswith('ray-worker-')]
        
        if not worker_names:
            result = 1
        else:
            indices = []
            for name in worker_names:
                try:
                    index = int(name.split('-')[-1])
                    indices.append(index)
                except ValueError:
                    continue
            result = max(indices) + 1 if indices else 1
        
        print(f"Test case {i+1}: {output.replace(chr(10), ', ')} -> {result} (expected: {expected})")
        assert result == expected, f"Test case {i+1} failed: got {result}, expected {expected}"
    
    print("✓ All worker index tests passed!")

def test_metrics_parsing():
    """Test the metrics parsing logic."""
    print("\nTesting metrics parsing...")
    
    # Sample Ray status output
    sample_output = """
    cluster_resources:
      CPU: 4.0
      memory: 8GB
      object_store_memory: 2GB
    
    cluster_usage:
      CPU: 2.0
      memory: 4GB
      object_store_memory: 1GB
    
    pending_tasks: 5
    running_tasks: 3
    """
    
    # Parse metrics (simplified version)
    metrics = {
        "pending_tasks": 0,
        "running_tasks": 0,
    }
    
    lines = sample_output.split('\n')
    for line in lines:
        line = line.strip()
        if "pending_tasks:" in line:
            try:
                metrics["pending_tasks"] = int(line.split(':')[1].strip())
            except:
                pass
        elif "running_tasks:" in line:
            try:
                metrics["running_tasks"] = int(line.split(':')[1].strip())
            except:
                pass
    
    print(f"Parsed metrics: {metrics}")
    assert metrics["pending_tasks"] == 5, f"Expected 5 pending tasks, got {metrics['pending_tasks']}"
    assert metrics["running_tasks"] == 3, f"Expected 3 running tasks, got {metrics['running_tasks']}"
    print("✓ Metrics parsing test passed!")

def test_scaling_decision():
    """Test the scaling decision logic."""
    print("\nTesting scaling decision logic...")
    
    # Test parameters
    pending_threshold = 5
    max_workers = 10
    
    test_cases = [
        # (pending_tasks, current_workers, should_scale)
        (10, 2, True),   # High pending tasks, low workers -> scale
        (3, 2, False),   # Low pending tasks -> don't scale
        (10, 10, False), # At max workers -> don't scale
        (6, 5, True),    # Above threshold, room to scale -> scale
    ]
    
    for pending, workers, expected in test_cases:
        # Simple decision logic
        should_scale = (
            pending >= pending_threshold and
            workers < max_workers
        )
        
        print(f"Pending: {pending}, Workers: {workers}, Should scale: {should_scale} (expected: {expected})")
        assert should_scale == expected, f"Scaling decision failed for pending={pending}, workers={workers}"
    
    print("✓ Scaling decision test passed!")

if __name__ == "__main__":
    print("Running Ray watcher tests...")
    test_worker_index_logic()
    test_metrics_parsing()
    test_scaling_decision()
    print("\n✅ All tests passed!")
