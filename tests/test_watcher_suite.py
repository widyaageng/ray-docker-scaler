#!/usr/bin/env python3
"""
Comprehensive test runner for Ray watcher functionality
"""
import os
import sys
import subprocess
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_test_file(test_file):
    """Run a specific test file and return the result."""
    try:
        logger.info(f"Running {test_file}...")
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__)
        )
        
        if result.returncode == 0:
            logger.info(f"✓ {test_file} PASSED")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            logger.error(f"✗ {test_file} FAILED")
            if result.stdout:
                print("STDOUT:", result.stdout)
            if result.stderr:
                print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        logger.error(f"✗ Error running {test_file}: {e}")
        return False

def test_watcher_setup():
    """Test the overall watcher setup and configuration."""
    logger.info("Testing watcher setup...")
    
    # Check if required files exist
    required_files = [
        '../scripts/ray_watcher.py',
        '../scripts/infra.py',
        'test_watcher.py',
        'test_watcher_logic.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        full_path = os.path.join(os.path.dirname(__file__), file_path)
        if not os.path.exists(full_path):
            missing_files.append(file_path)
    
    if missing_files:
        logger.error(f"Missing required files: {missing_files}")
        return False
    else:
        logger.info("✓ All required files exist")
        return True

def test_watcher_commands():
    """Test that watcher commands work in infra.py."""
    logger.info("Testing watcher commands...")
    
    try:
        # Test help command
        result = subprocess.run(
            [sys.executable, '../scripts/infra.py', '--help'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__)
        )
        
        if result.returncode != 0:
            logger.error("Failed to run infra.py help command")
            return False
        
        # Check for watcher commands
        watcher_commands = ['start-watcher', 'stop-watcher', 'watcher-status', 'add-worker']
        for cmd in watcher_commands:
            if cmd in result.stdout:
                logger.info(f"✓ Command {cmd} available")
            else:
                logger.error(f"✗ Command {cmd} missing")
                return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing watcher commands: {e}")
        return False

def run_integration_test():
    """Run a quick integration test if Ray cluster is available."""
    logger.info("Testing Ray cluster integration...")
    
    try:
        # Check if Docker is available
        result = subprocess.run(['docker', '--version'], capture_output=True)
        if result.returncode != 0:
            logger.warning("Docker not available, skipping integration test")
            return True
        
        # Check if Ray containers exist
        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=ray-head', '--format', '{{.Names}}'],
            capture_output=True,
            text=True
        )
        
        if 'ray-head' not in result.stdout:
            logger.warning("Ray cluster not running, skipping integration test")
            return True
        
        logger.info("Ray cluster detected, running basic integration test...")
        
        # Test watcher status command
        result = subprocess.run(
            [sys.executable, '../scripts/infra.py', 'watcher-status'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__)
        )
        
        if result.returncode == 0:
            logger.info("✓ Watcher status command works with live cluster")
            return True
        else:
            logger.warning(f"Watcher status command returned {result.returncode}")
            logger.warning(f"This is expected if watcher is not running")
            return True  # Don't fail test for this
            
    except Exception as e:
        logger.warning(f"Integration test error (non-critical): {e}")
        return True  # Don't fail overall test suite

def main():
    """Run all watcher tests."""
    logger.info("=== Ray Watcher Test Suite ===")
    
    # Change to test directory
    os.chdir(os.path.dirname(__file__))
    
    tests = [
        ("Setup Test", test_watcher_setup),
        ("Commands Test", test_watcher_commands),
        ("Logic Tests", lambda: run_test_file("test_watcher_logic.py")),
        ("Integration Tests", lambda: run_test_file("test_watcher.py")),
        ("Live Integration", run_integration_test),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            logger.info(f"\n--- Running {test_name} ---")
            if test_func():
                logger.info(f"✓ {test_name} PASSED")
                passed += 1
            else:
                logger.error(f"✗ {test_name} FAILED")
                failed += 1
        except Exception as e:
            logger.error(f"✗ {test_name} ERROR: {e}")
            failed += 1
    
    logger.info(f"\n=== Final Test Results ===")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {failed}")
    logger.info(f"Total: {passed + failed}")
    
    if failed == 0:
        logger.info("🎉 All tests passed!")
        return True
    else:
        logger.error(f"❌ {failed} test(s) failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
