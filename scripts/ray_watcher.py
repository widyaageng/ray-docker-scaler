#!/usr/bin/env python3
"""
Ray Watcher Service

This service monitors Ray cluster metrics and automatically provisions
new workers when pending tasks exceed the configured threshold.
"""

import time
import subprocess
import logging
import os
import re
import sys
from datetime import datetime, timedelta
from typing import Dict, Optional


# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ray-watcher')

# Global state
last_scale_up: Optional[datetime] = None

# Configuration (can be overridden via environment variables)
CHECK_INTERVAL = int(os.getenv('WATCHER_CHECK_INTERVAL', '120'))
PENDING_TASK_THRESHOLD = int(os.getenv('WATCHER_PENDING_THRESHOLD', '5'))
MAX_WORKERS = int(os.getenv('WATCHER_MAX_WORKERS', '10'))
SCALE_UP_COOLDOWN = int(os.getenv('WATCHER_COOLDOWN', '300'))
RAY_IMAGE_VERSION = os.getenv('RAY_IMAGE_VERSION', 'rayproject/ray:2.47.1.aeaf41-py39-cpu')


def run_command(command: str, check: bool = False) -> Optional[subprocess.CompletedProcess]:
    """
    Run a shell command and return the result.
    
    Args:
        command: Command to run
        check: Whether to raise exception on failure
        
    Returns:
        CompletedProcess result or None if failed
    """
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if check and result.returncode != 0:
            logger.error(f"Command failed: {command}")
            logger.error(f"STDERR: {result.stderr}")
            return None
        return result
    except Exception as e:
        logger.error(f"Error running command: {e}")
        return None


def get_cluster_metrics() -> Optional[Dict[str, int]]:
    """
    Get Ray cluster metrics including pending tasks.
    
    Returns:
        Dictionary with cluster metrics or None if failed
    """
    try:
        # Get Ray status from head node
        result = run_command("docker exec ray-head ray status --address=auto", check=False)
        if not result or result.returncode != 0:
            logger.warning("Could not get Ray status from head node")
            return None
        
        status_output = result.stdout
        metrics = {
            "pending_tasks": 0,
            "running_tasks": 0,
            "workers": 0
        }
        
        # Parse status output for task information
        lines = status_output.split('\n')
        for line in lines:
            line = line.strip()
            # Look for task information in various formats
            if "pending" in line.lower() and "task" in line.lower():
                try:
                    match = re.search(r'(\d+)\s+pending', line, re.IGNORECASE)
                    if match:
                        metrics["pending_tasks"] = int(match.group(1))
                except:
                    pass
            elif "running" in line.lower() and "task" in line.lower():
                try:
                    match = re.search(r'(\d+)\s+running', line, re.IGNORECASE)
                    if match:
                        metrics["running_tasks"] = int(match.group(1))
                except:
                    pass
        
        # Get current worker count from Docker
        result = run_command("docker ps --filter name=ray-worker --format '{{.Names}}'", check=False)
        if result and result.stdout.strip():
            workers = [
                w.strip() for w in result.stdout.strip().split('\n') 
                if w.strip() and w.startswith('ray-worker')
            ]
            metrics["workers"] = len(workers)
        else:
            metrics["workers"] = 0
        
        return metrics
    except Exception as e:
        logger.error(f"Error getting cluster metrics: {e}")
        return None


def should_scale_up(metrics: Dict[str, int]) -> bool:
    """
    Determine if we should scale up based on current metrics.
    
    Args:
        metrics: Current cluster metrics
        
    Returns:
        True if should scale up, False otherwise
    """
    global last_scale_up
    
    if not metrics:
        return False
    
    # Check if we have pending tasks above threshold
    if metrics["pending_tasks"] < PENDING_TASK_THRESHOLD:
        return False
    
    # Check if we're already at max workers
    if metrics["workers"] >= MAX_WORKERS:
        logger.info(f"Already at maximum workers ({MAX_WORKERS})")
        return False
    
    # Check cooldown period
    if last_scale_up:
        time_since_last_scale = datetime.now() - last_scale_up
        if time_since_last_scale.total_seconds() < SCALE_UP_COOLDOWN:
            remaining = SCALE_UP_COOLDOWN - time_since_last_scale.total_seconds()
            logger.info(f"Scale-up cooldown: {remaining:.0f} seconds remaining")
            return False
    
    return True


def get_next_worker_index() -> int:
    """
    Get the next available worker index.
    
    Returns:
        Next worker index to use
    """
    try:
        result = run_command("docker ps --filter name=ray-worker --format '{{.Names}}'", check=False)
        if not result or not result.stdout.strip():
            return 1
        
        worker_names = [
            w.strip() for w in result.stdout.strip().split('\n') 
            if w.strip() and w.startswith('ray-worker-')
        ]
        
        if not worker_names:
            return 1
        
        # Extract indices and find the highest
        indices = []
        for name in worker_names:
            try:
                index = int(name.split('-')[-1])
                indices.append(index)
            except ValueError:
                continue
        
        return max(indices) + 1 if indices else 1
    except Exception as e:
        logger.error(f"Error getting next worker index: {e}")
        return 1


def scale_up_worker() -> bool:
    """
    Scale up by adding a new Ray worker.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get next worker index
        worker_index = get_next_worker_index()
        worker_name = f"ray-worker-{worker_index}"
        
        logger.info(f"Scaling up: Adding new Ray worker {worker_name}")
        
        # Start new worker container
        command = f"""
        docker run -d \\
            --name {worker_name} \\
            --network ray-cluster \\
            --shm-size=2gb \\
            --init \\
            -v /workspace:/workspace \\
            -v /workspace/logs:/tmp/ray \\
            -w /workspace \\
            -e RAY_HEAD_ADDRESS=ray-head:10000 \\
            -e RAY_DISABLE_IMPORT_WARNING=1 \\
            {RAY_IMAGE_VERSION} \\
            bash -c 'sleep 5 && RAY_DISABLE_IMPORT_WARNING=1 ray start --address=ray-head:10000 --object-store-memory=1000000000 --num-cpus=1 --disable-usage-stats && sleep infinity'
        """
        
        result = run_command(command.replace('\n', ' ').strip(), check=False)
        if result and result.returncode == 0:
            logger.info(f"Successfully started {worker_name}")
            time.sleep(10)  # Wait for worker to connect
            return True
        else:
            logger.error(f"Failed to start {worker_name}")
            if result:
                logger.error(f"Error output: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error scaling up worker: {e}")
        return False


def main():
    """Main watcher loop."""
    global last_scale_up
    
    logger.info("Ray Watcher started")
    logger.info(f"Check interval: {CHECK_INTERVAL} seconds")
    logger.info(f"Pending task threshold: {PENDING_TASK_THRESHOLD}")
    logger.info(f"Max workers: {MAX_WORKERS}")
    logger.info(f"Scale-up cooldown: {SCALE_UP_COOLDOWN} seconds")
    
    while True:
        try:
            # Get cluster metrics
            metrics = get_cluster_metrics()
            if metrics:
                logger.info(
                    f"Cluster metrics - Pending: {metrics['pending_tasks']}, "
                    f"Running: {metrics['running_tasks']}, Workers: {metrics['workers']}"
                )
                
                # Check if we should scale up
                if should_scale_up(metrics):
                    if scale_up_worker():
                        last_scale_up = datetime.now()
                        logger.info(f"Scaled up at {last_scale_up}")
                    else:
                        logger.error("Scale-up failed")
            else:
                logger.warning("Could not get cluster metrics")
            
            # Wait for next check
            time.sleep(CHECK_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("Ray Watcher stopped")
            break
        except Exception as e:
            logger.error(f"Error in watcher main loop: {e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
