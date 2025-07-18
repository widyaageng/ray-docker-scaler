#!/usr/bin/env python3
"""
Ray Watcher Service

This service monitors Ray cluster metrics and automatically provisions
new workers when pending tasks exceed the configured threshold.
"""

import time
import logging
import os
import sys
import subprocess
from datetime import datetime, timedelta
import requests
from typing import Dict, Optional, List
import ray
from ray.util.state import list_nodes


# Configure logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('ray-watcher')

# Global state
last_scale_up: Optional[datetime] = None

# Configuration (can be overridden via environment variables)
CHECK_INTERVAL = int(os.getenv('WATCHER_CHECK_INTERVAL', '10'))
PENDING_TASK_THRESHOLD = int(os.getenv('WATCHER_PENDING_THRESHOLD', '0'))
MAX_WORKERS = int(os.getenv('WATCHER_MAX_WORKERS', '5'))
SCALE_UP_COOLDOWN = int(os.getenv('WATCHER_COOLDOWN', '60'))
RAY_HEAD_ADDRESS = os.getenv('RAY_HEAD_ADDRESS', 'localhost:10001')
RAY_DASHBOARD_METRIC_API = os.getenv('RAY_DASHBOARD_METRIC_API', 'http://localhost:8265/api')


def initialize_ray_connection():
    """
    Initialize connection to Ray cluster.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        if not ray.is_initialized():
            logger.info(f"Connecting to Ray cluster client at {RAY_HEAD_ADDRESS}")
            ray.init(address=f"ray://{RAY_HEAD_ADDRESS}")
            logger.info(f"Connected to Ray cluster client at {RAY_HEAD_ADDRESS}")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Ray cluster client: {e}")
        return False


def get_cluster_metrics() -> Optional[Dict[str, int]]:
    """
    Get Ray cluster metrics including pending tasks.
    
    This function combines multiple data sources to estimate cluster load:
    1. Ray API for cluster resources and node information
    2. Ray Dashboard API for accurate pending task metrics
    3. CPU-based heuristics as fallback for pending task estimation
    
    The pending task estimation logic works as follows:
    - Primary: Attempts to fetch pending tasks from Ray Dashboard API resource demands
    - Fallback: If API fails or returns 0 pending tasks, uses CPU-based estimation
    - CPU estimation: If there are pending tasks > 0, finds the smallest available CPU 
      spec from nodes and uses that as the estimated pending task count
    
    Returns:
        Dictionary with cluster metrics containing:
        - pending_tasks: Estimated number of pending tasks waiting for resources
        - running_tasks: Currently executing tasks (estimated from CPU usage)
        - workers: Number of worker nodes (excludes head node)
        - total_cpus: Total CPU cores available in cluster
        - available_cpus: Currently available (unused) CPU cores
        - used_cpus: Currently utilized CPU cores
        
        Returns None if failed to connect to Ray cluster or gather metrics.
        
    Note:
        Pending task estimation is heuristic-based since Ray doesn't directly expose
        this metric in a simple API. The function prioritizes Dashboard API data
        but falls back to resource utilization patterns for estimation.
    """
    try:
        if not ray.is_initialized():
            if not initialize_ray_connection():
                return None
        
        # Get cluster status using Ray API
        cluster_status = ray.cluster_resources()
        cluster_available = ray.available_resources()
        
        # Get node information - use a simpler approach
        nodes = ray.nodes()
        # Count total nodes and subtract 1 for head node
        total_nodes = len([node for node in nodes if 'Alive' in node.keys()])
        worker_nodes_count = max(0, total_nodes - 1)  # Assume 1 head node
        nodes_cpu_sorted = [node['Resources'].get('CPU', 0) for node in nodes if 'Resources' in node]
        nodes_cpu_sorted.sort()
        
        # Get task information from Ray's internal state
        # Note: Ray doesn't directly expose pending tasks count in a simple way
        # We'll use a heuristic based on resource usage
        total_cpus = cluster_status.get('CPU', 0)
        available_cpus = cluster_available.get('CPU', 0)
        used_cpus = total_cpus - available_cpus
        
        # Estimate pending tasks based on resource utilization
        # This is a simplified approach - in practice, you might want to
        # use Ray's task monitoring APIs for more accurate metrics
        estimated_running_tasks = int(used_cpus)
        
        # For pending tasks, we'll check if resources are fully utilized
        # from metrics api
        estimated_pending_tasks = 0
        try:
            _resp = requests.get(RAY_DASHBOARD_METRIC_API + '/cluster_status')
            if _resp.status_code == 200:
                logger.info(f"Succeed get cluster status from API: {_resp}")

                # TODO: this parsing is highly opinionated and may change in future
                # versions of Ray Dashboard API
                # Adjust the parsing based on actual API response structure
                _resource_demands = _resp.json().get('data', {})\
                            .get('clusterStatus', {})\
                            .get('loadMetricsReport', {})\
                            .get('resourceDemand', [])
                if len(_resource_demands) > 0:
                    for demand_elem in _resource_demands:
                        # Each demand_elem is a list of demands, sum them up
                        if len(demand_elem) > 1:
                            estimated_pending_tasks += demand_elem[0].get('CPU')*demand_elem[1]
        except requests.RequestException as e:
            logger.error(f"Failed to fetch cluster status from API: {e}")
            pass

        # If we detected pending tasks from Dashboard API, refine the estimate
        # by using the smallest available CPU spec from nodes as a more realistic
        # pending task count (assumes each task needs at least one CPU unit)
        if estimated_pending_tasks > 0:
            for cpu_spec in nodes_cpu_sorted:
                if cpu_spec > 0:
                    estimated_pending_tasks = cpu_spec
                    break

        metrics = {
            "pending_tasks": estimated_pending_tasks,
            "running_tasks": estimated_running_tasks,
            "workers": worker_nodes_count,
            "total_cpus": total_cpus,
            "available_cpus": available_cpus,
            "used_cpus": used_cpus
        }
        
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
    is_to_scale_up = False
    
    if not metrics:
        return False
    
    # Check if we're already at max workers
    if metrics["workers"] >= MAX_WORKERS:
        logger.warning(f"Already at maximum workers ({MAX_WORKERS})")
        return False
    
    # Check if we have pending tasks above threshold
    if metrics["pending_tasks"] > PENDING_TASK_THRESHOLD:
        is_to_scale_up = True

    # Check cooldown period
    if last_scale_up and is_to_scale_up:
        time_since_last_scale = datetime.now() - last_scale_up
        if time_since_last_scale.total_seconds() < SCALE_UP_COOLDOWN:
            remaining = SCALE_UP_COOLDOWN - time_since_last_scale.total_seconds()
            logger.info(f"Scale-up cooldown: {remaining:.0f} seconds remaining")
            return False
        return True
    
    if last_scale_up is None and is_to_scale_up:
        # If we have never scaled up, allow scaling
        return True
    
    return False


def scale_up_worker() -> bool:
    """
    Scale up by adding a new Ray worker using infra.py add-worker command.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Scaling up: Adding new Ray worker")
        
        # Get the path to the infra.py script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        infra_script_path = os.path.join(script_dir, "infra.py")
        
        # Check if infra.py exists
        if not os.path.exists(infra_script_path):
            logger.error(f"infra.py script not found at {infra_script_path}")
            return False
        
        # Run the add-worker command
        command = [
            sys.executable, infra_script_path, "add-worker",
            "--num-cpus", str(os.getenv('WATCHER_NUM_CPUS', '1')),
            "--num-gpus", str(os.getenv('WATCHER_NUM_GPUS', '0')),
            "--object-store-memory", os.getenv('WATCHER_OBJECT_STORE_MEMORY', '1GB')
        ]
        
        logger.info(f"Running command: {' '.join(command)}")
        result = subprocess.run(
            command,
            cwd=script_dir,
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )
        
        if result.returncode == 0:
            logger.info("Successfully added new Ray worker")
            if result.stdout:
                logger.info(f"Command output: {result.stdout.strip()}")
            return True
        else:
            logger.error(f"Failed to add Ray worker (exit code: {result.returncode})")
            if result.stderr:
                logger.error(f"Error output: {result.stderr.strip()}")
            if result.stdout:
                logger.error(f"Command output: {result.stdout.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error("Timeout while adding Ray worker")
        return False
    except Exception as e:
        logger.error(f"Error in scale-up logic: {e}")
        return False


def main():
    """Main watcher loop."""
    global last_scale_up
    
    logger.info("Ray Watcher started")
    logger.info(f"Ray head address: {RAY_HEAD_ADDRESS}")
    logger.info(f"Check interval: {CHECK_INTERVAL} seconds")
    logger.info(f"Pending task threshold: {PENDING_TASK_THRESHOLD}")
    logger.info(f"Max workers: {MAX_WORKERS}")
    logger.info(f"Scale-up cooldown: {SCALE_UP_COOLDOWN} seconds")
    
    # Initialize Ray connection
    if not initialize_ray_connection():
        logger.error("Failed to initialize Ray connection. Exiting.")
        sys.exit(1)
    
    while True:
        try:
            # Get cluster metrics
            metrics = get_cluster_metrics()
            if metrics:
                logger.info(
                    f"Cluster metrics - Pending: {metrics['pending_tasks']}, "
                    f"Running: {metrics['running_tasks']}, Workers: {metrics['workers']}, "
                    f"CPU Usage: {metrics['used_cpus']:.1f}/{metrics['total_cpus']:.1f}"
                )
                
                # Check if we should scale up
                if should_scale_up(metrics):
                    if scale_up_worker():
                        last_scale_up = datetime.now()
                        logger.info(f"Scaled up at {last_scale_up}")
                    else:
                        logger.error("Scale-up failed")
                else:
                    logger.info("No scaling needed")
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
    
    # Cleanup
    try:
        if ray.is_initialized():
            ray.shutdown()
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")


if __name__ == "__main__":
    main()
