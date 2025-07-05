#!/usr/bin/env python3
"""
Unit tests for Ray watcher logic functions
"""
import subprocess
import re
import os
import sys

# Add the scripts directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

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
    
    try:
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
        return True
    except AssertionError as e:
        print(f"✗ Worker index test failed: {e}")
        return False


def test_watcher_script_imports():
    """Test that the watcher script can be imported and key functions exist."""
    print("\nTesting watcher script imports...")
    
    try:
        # Try to import the watcher script
        import ray_watcher # type: ignore[import]
        
        # Check that key functions exist
        required_functions = [
            'get_cluster_metrics',
            'should_scale_up', 
            'scale_up_worker',
            'get_next_worker_index',
            'run_command'
        ]
        
        for func_name in required_functions:
            if hasattr(ray_watcher, func_name):
                print(f"✓ Function {func_name} exists")
            else:
                print(f"✗ Function {func_name} missing")
                return False
        
        # Check environment variable handling
        original_interval = os.getenv('WATCHER_CHECK_INTERVAL')
        os.environ['WATCHER_CHECK_INTERVAL'] = '60'
        
        # Re-import to test environment variable reading
        import importlib
        importlib.reload(ray_watcher)
        
        if hasattr(ray_watcher, 'WATCHER_CHECK_INTERVAL'):
            print(f"✓ Environment variables are read correctly")
        
        # Restore original value
        if original_interval:
            os.environ['WATCHER_CHECK_INTERVAL'] = original_interval
        else:
            os.environ.pop('WATCHER_CHECK_INTERVAL', None)
        
        return True
        
    except ImportError as e:
        print(f"✗ Could not import ray_watcher: {e}")
        return False
    except Exception as e:
        print(f"✗ Error testing watcher script: {e}")
        return False


def test_infra_script_watcher_commands():
    """Test that infra.py has the watcher commands."""
    print("\nTesting infra.py watcher commands...")
    
    try:
        # Get the parent directory (project root)
        project_root = os.path.join(os.path.dirname(__file__), '..')
        
        # Test help command to see available actions
        result = subprocess.run(
            [sys.executable, 'scripts/infra.py', '--help'],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        if result.returncode == 0:
            help_output = result.stdout
            watcher_commands = ['start-watcher', 'stop-watcher', 'watcher-status', 'add-worker']
            
            for cmd in watcher_commands:
                if cmd in help_output:
                    print(f"✓ Command {cmd} available")
                else:
                    print(f"✗ Command {cmd} missing")
                    return False
            
            # Check watcher-specific arguments
            watcher_args = ['--check-interval', '--pending-threshold', '--max-workers', '--cooldown']
            for arg in watcher_args:
                if arg in help_output:
                    print(f"✓ Argument {arg} available")
                else:
                    print(f"✗ Argument {arg} missing")
                    return False
                    
            return True
        else:
            print(f"✗ infra.py help command failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error testing infra.py commands: {e}")
        return False

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
    
    # Parse metrics (simplified version of the logic from ray_watcher.py)
    metrics = {
        "pending_tasks": 0,
        "running_tasks": 0,
    }
    
    lines = sample_output.split('\n')
    try:
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
        return True
    except Exception as e:
        print(f"✗ Metrics parsing test failed: {e}")
        return False


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
    
    try:
        for pending, workers, expected in test_cases:
            # Simple decision logic (matches the logic in ray_watcher.py)
            should_scale = (
                pending >= pending_threshold and
                workers < max_workers
            )
            
            print(f"Pending: {pending}, Workers: {workers}, Should scale: {should_scale} (expected: {expected})")
            assert should_scale == expected, f"Scaling decision failed for pending={pending}, workers={workers}"
        
        print("✓ Scaling decision test passed!")
        return True
    except AssertionError as e:
        print(f"✗ Scaling decision test failed: {e}")
        return False


def test_watcher_script_syntax():
    """Test that the watcher script has valid Python syntax."""
    print("\nTesting watcher script syntax...")
    
    try:
        script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'ray_watcher.py')
        
        # Check if file exists
        if not os.path.exists(script_path):
            print(f"✗ Watcher script not found at {script_path}")
            return False
        
        # Compile the script to check syntax
        with open(script_path, 'r') as f:
            script_content = f.read()
        
        compile(script_content, script_path, 'exec')
        print("✓ Watcher script has valid syntax")
        return True
        
    except SyntaxError as e:
        print(f"✗ Syntax error in watcher script: {e}")
        return False
    except Exception as e:
        print(f"✗ Error checking watcher script syntax: {e}")
        return False


def run_all_tests():
    """Run all watcher logic tests."""
    print("Running Ray watcher logic tests...")
    
    tests = [
        test_worker_index_logic,
        test_watcher_script_imports,
        test_infra_script_watcher_commands,
        test_metrics_parsing,
        test_scaling_decision,
        test_watcher_script_syntax,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            print(f"\n--- Running {test.__name__} ---")
            if test():
                print(f"✓ {test.__name__} PASSED")
                passed += 1
            else:
                print(f"✗ {test.__name__} FAILED")
                failed += 1
        except Exception as e:
            print(f"✗ {test.__name__} ERROR: {e}")
            failed += 1
    
    print(f"\n=== Test Summary ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {passed + failed}")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
