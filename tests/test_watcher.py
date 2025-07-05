#!/usr/bin/env python3
"""
Test script to verify Ray watcher functionality
"""
import ray
import time
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_watcher_functionality():
    """Test the Ray watcher by generating pending tasks."""
    logger.info("Testing Ray watcher functionality...")
    
    # Connect to Ray cluster
    try:
        ray.init(address="ray://localhost:10001")
        logger.info("Connected to Ray cluster")
    except Exception as e:
        logger.error(f"Failed to connect to Ray cluster: {e}")
        return False
    
    # Create some tasks that will be pending
    @ray.remote
    def long_running_task(task_id):
        """A task that takes some time to complete."""
        logger.info(f"Starting long running task {task_id}")
        time.sleep(30)  # Sleep for 30 seconds
        return f"Task {task_id} completed"
    
    # Submit multiple tasks to create pending tasks
    logger.info("Submitting tasks to create pending workload...")
    futures = []
    for i in range(10):
        future = long_running_task.remote(i)
        futures.append(future)
        logger.info(f"Submitted task {i}")
    
    # Wait a bit for tasks to be pending
    logger.info("Waiting for tasks to be pending...")
    time.sleep(5)
    
    # Check Ray status
    try:
        result = subprocess.run(
            ["ray", "status"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Ray status:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get Ray status: {e}")
    
    # Wait for watcher to potentially scale up
    logger.info("Waiting for watcher to potentially scale up (5 minutes)...")
    time.sleep(300)
    
    # Check final status
    try:
        result = subprocess.run(
            ["ray", "status"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info(f"Final Ray status:\n{result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to get final Ray status: {e}")
    
    # Wait for tasks to complete
    logger.info("Waiting for tasks to complete...")
    results = ray.get(futures)
    logger.info(f"All tasks completed: {len(results)} results")
    
    ray.shutdown()
    return True

if __name__ == "__main__":
    test_watcher_functionality()
