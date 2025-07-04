#!/usr/bin/env python3
"""
Custom Ray Autoscaler

This script implements custom autoscaling logic for the Ray cluster based on
workload demands and resource utilization.
"""

import time
import logging
import argparse
import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import threading

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ray

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ResourceMonitor:
    """Monitor cluster resource utilization."""

    def __init__(self):
        """Initialize the resource monitor."""
        self.history: List[Dict[str, Any]] = []
        self.max_history = 100

    def get_current_utilization(self) -> Dict[str, Any]:
        """
        Get current cluster resource utilization.

        Returns:
            Dictionary containing current utilization metrics
        """
        try:
            if not ray.is_initialized():
                return {"error": "Ray not initialized"}

            cluster_resources = ray.cluster_resources()
            available_resources = ray.available_resources()

            # Calculate utilization percentages
            utilization = {}

            for resource, total in cluster_resources.items():
                available = available_resources.get(resource, 0)
                used = total - available
                utilization[resource] = {
                    "total": total,
                    "used": used,
                    "available": available,
                    "utilization_percent": (used / total) * 100 if total > 0 else 0,
                }

            # Get node information
            nodes = ray.nodes()
            alive_nodes = [node for node in nodes if node["Alive"]]

            current_time = datetime.now()

            metrics = {
                "timestamp": current_time.isoformat(),
                "nodes": {
                    "total": len(nodes),
                    "alive": len(alive_nodes),
                    "dead": len(nodes) - len(alive_nodes),
                },
                "resources": utilization,
                "cluster_resources": cluster_resources,
                "available_resources": available_resources,
            }

            # Add to history
            self.history.append(metrics)
            if len(self.history) > self.max_history:
                self.history.pop(0)

            return metrics

        except Exception as e:
            logger.error(f"Error getting utilization: {e}")
            return {"error": str(e)}

    def get_average_utilization(self, minutes: int = 5) -> Dict[str, float]:
        """
        Get average utilization over the specified time period.

        Args:
            minutes: Time period in minutes

        Returns:
            Dictionary containing average utilization
        """
        cutoff_time = datetime.now() - timedelta(minutes=minutes)

        recent_metrics = [
            m
            for m in self.history
            if datetime.fromisoformat(m["timestamp"]) > cutoff_time
        ]

        if not recent_metrics:
            return {}

        # Calculate averages
        avg_utilization = {}

        for metrics in recent_metrics:
            for resource, data in metrics.get("resources", {}).items():
                if resource not in avg_utilization:
                    avg_utilization[resource] = []
                avg_utilization[resource].append(data["utilization_percent"])

        # Compute averages
        result = {}
        for resource, values in avg_utilization.items():
            result[resource] = sum(values) / len(values)

        return result


class AutoscalerPolicy:
    """Define autoscaling policies and rules."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize autoscaler policy.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.min_nodes = config.get("min_nodes", 1)
        self.max_nodes = config.get("max_nodes", 10)
        self.target_cpu_utilization = config.get("target_cpu_utilization", 70.0)
        self.scale_up_threshold = config.get("scale_up_threshold", 80.0)
        self.scale_down_threshold = config.get("scale_down_threshold", 30.0)
        self.cooldown_period = config.get("cooldown_period", 300)  # seconds
        self.last_scale_time = datetime.min

    def should_scale_up(
        self, current_metrics: Dict[str, Any], avg_utilization: Dict[str, float]
    ) -> bool:
        """
        Determine if cluster should scale up.

        Args:
            current_metrics: Current cluster metrics
            avg_utilization: Average utilization metrics

        Returns:
            True if should scale up, False otherwise
        """
        # Check cooldown period
        if (datetime.now() - self.last_scale_time).seconds < self.cooldown_period:
            return False

        # Check if we're at max capacity
        current_nodes = current_metrics.get("nodes", {}).get("alive", 0)
        if current_nodes >= self.max_nodes:
            return False

        # Check CPU utilization
        cpu_utilization = avg_utilization.get("CPU", 0)
        if cpu_utilization > self.scale_up_threshold:
            logger.info(
                f"Scale up triggered: CPU utilization {cpu_utilization:.1f}% > {self.scale_up_threshold}%"
            )
            return True

        # Check if resources are heavily utilized
        for resource, utilization in avg_utilization.items():
            if utilization > self.scale_up_threshold:
                logger.info(
                    f"Scale up triggered: {resource} utilization {utilization:.1f}% > {self.scale_up_threshold}%"
                )
                return True

        return False

    def should_scale_down(
        self, current_metrics: Dict[str, Any], avg_utilization: Dict[str, float]
    ) -> bool:
        """
        Determine if cluster should scale down.

        Args:
            current_metrics: Current cluster metrics
            avg_utilization: Average utilization metrics

        Returns:
            True if should scale down, False otherwise
        """
        # Check cooldown period
        if (datetime.now() - self.last_scale_time).seconds < self.cooldown_period:
            return False

        # Check if we're at min capacity
        current_nodes = current_metrics.get("nodes", {}).get("alive", 0)
        if current_nodes <= self.min_nodes:
            return False

        # Check if all resources are underutilized
        all_resources_low = True
        for resource, utilization in avg_utilization.items():
            if utilization > self.scale_down_threshold:
                all_resources_low = False
                break

        if all_resources_low and avg_utilization:
            cpu_utilization = avg_utilization.get("CPU", 100)
            logger.info(
                f"Scale down triggered: CPU utilization {cpu_utilization:.1f}% < {self.scale_down_threshold}%"
            )
            return True

        return False

    def record_scaling_action(self):
        """Record that a scaling action was taken."""
        self.last_scale_time = datetime.now()


class RayAutoscaler:
    """Main autoscaler class."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the autoscaler.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.monitor = ResourceMonitor()
        self.policy = AutoscalerPolicy(config)
        self.running = False
        self.monitoring_interval = config.get("monitoring_interval", 30)  # seconds
        self.dry_run = config.get("dry_run", False)

    def scale_up(self, current_metrics: Dict[str, Any]) -> bool:
        """
        Scale up the cluster.

        Args:
            current_metrics: Current cluster metrics

        Returns:
            True if successful, False otherwise
        """
        try:
            current_nodes = current_metrics.get("nodes", {}).get("alive", 0)
            target_nodes = min(current_nodes + 1, self.policy.max_nodes)

            logger.info(
                f"Scaling up cluster from {current_nodes} to {target_nodes} nodes"
            )

            if self.dry_run:
                logger.info("DRY RUN: Would scale up cluster")
                return True

            # In a real implementation, you would add logic here to:
            # 1. Launch new nodes (e.g., using cloud provider APIs)
            # 2. Configure them to join the Ray cluster
            # 3. Wait for them to be ready

            # For now, we'll just log the action
            logger.info("Scale up action would be executed here")
            self.policy.record_scaling_action()

            return True

        except Exception as e:
            logger.error(f"Failed to scale up: {e}")
            return False

    def scale_down(self, current_metrics: Dict[str, Any]) -> bool:
        """
        Scale down the cluster.

        Args:
            current_metrics: Current cluster metrics

        Returns:
            True if successful, False otherwise
        """
        try:
            current_nodes = current_metrics.get("nodes", {}).get("alive", 0)
            target_nodes = max(current_nodes - 1, self.policy.min_nodes)

            logger.info(
                f"Scaling down cluster from {current_nodes} to {target_nodes} nodes"
            )

            if self.dry_run:
                logger.info("DRY RUN: Would scale down cluster")
                return True

            # In a real implementation, you would add logic here to:
            # 1. Gracefully drain workloads from nodes
            # 2. Remove nodes from the cluster
            # 3. Terminate the nodes

            # For now, we'll just log the action
            logger.info("Scale down action would be executed here")
            self.policy.record_scaling_action()

            return True

        except Exception as e:
            logger.error(f"Failed to scale down: {e}")
            return False

    def run_once(self) -> Dict[str, Any]:
        """
        Run one iteration of the autoscaler.

        Returns:
            Dictionary containing iteration results
        """
        try:
            # Get current metrics
            current_metrics = self.monitor.get_current_utilization()

            if "error" in current_metrics:
                logger.error(f"Error getting metrics: {current_metrics['error']}")
                return {"status": "error", "error": current_metrics["error"]}

            # Get average utilization
            avg_utilization = self.monitor.get_average_utilization(minutes=5)

            # Log current status
            cpu_util = avg_utilization.get("CPU", 0)
            alive_nodes = current_metrics.get("nodes", {}).get("alive", 0)

            logger.info(f"Cluster status: {alive_nodes} nodes, CPU: {cpu_util:.1f}%")

            # Make scaling decisions
            action_taken = None

            if self.policy.should_scale_up(current_metrics, avg_utilization):
                if self.scale_up(current_metrics):
                    action_taken = "scale_up"
            elif self.policy.should_scale_down(current_metrics, avg_utilization):
                if self.scale_down(current_metrics):
                    action_taken = "scale_down"

            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "metrics": current_metrics,
                "avg_utilization": avg_utilization,
                "action_taken": action_taken,
            }

        except Exception as e:
            logger.error(f"Error in autoscaler iteration: {e}")
            return {"status": "error", "error": str(e)}

    def start(self):
        """Start the autoscaler."""
        self.running = True
        logger.info(
            f"Starting autoscaler (monitoring interval: {self.monitoring_interval}s)"
        )

        while self.running:
            try:
                result = self.run_once()

                if result.get("action_taken"):
                    logger.info(f"Action taken: {result['action_taken']}")

                time.sleep(self.monitoring_interval)

            except KeyboardInterrupt:
                logger.info("Autoscaler interrupted by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error in autoscaler: {e}")
                time.sleep(self.monitoring_interval)

        logger.info("Autoscaler stopped")

    def stop(self):
        """Stop the autoscaler."""
        self.running = False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Ray Cluster Autoscaler")
    parser.add_argument(
        "--config", type=str, help="Path to autoscaler configuration file"
    )
    parser.add_argument(
        "--min-nodes", type=int, default=1, help="Minimum number of nodes"
    )
    parser.add_argument(
        "--max-nodes", type=int, default=10, help="Maximum number of nodes"
    )
    parser.add_argument(
        "--target-cpu",
        type=float,
        default=70.0,
        help="Target CPU utilization percentage",
    )
    parser.add_argument(
        "--scale-up-threshold",
        type=float,
        default=80.0,
        help="Scale up threshold percentage",
    )
    parser.add_argument(
        "--scale-down-threshold",
        type=float,
        default=30.0,
        help="Scale down threshold percentage",
    )
    parser.add_argument(
        "--monitoring-interval",
        type=int,
        default=30,
        help="Monitoring interval in seconds",
    )
    parser.add_argument(
        "--cooldown-period",
        type=int,
        default=300,
        help="Cooldown period between scaling actions in seconds",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Run in dry-run mode (no actual scaling)"
    )
    parser.add_argument("--once", action="store_true", help="Run once and exit")

    args = parser.parse_args()

    # Build configuration
    config = {
        "min_nodes": args.min_nodes,
        "max_nodes": args.max_nodes,
        "target_cpu_utilization": args.target_cpu,
        "scale_up_threshold": args.scale_up_threshold,
        "scale_down_threshold": args.scale_down_threshold,
        "monitoring_interval": args.monitoring_interval,
        "cooldown_period": args.cooldown_period,
        "dry_run": args.dry_run,
    }

    # Load config file if provided
    if args.config and os.path.exists(args.config):
        import json

        with open(args.config, "r") as f:
            file_config = json.load(f)
            config.update(file_config)

    logger.info(f"Autoscaler configuration: {config}")

    # Create and start autoscaler
    autoscaler = RayAutoscaler(config)

    if args.once:
        logger.info("Running autoscaler once...")
        result = autoscaler.run_once()
        logger.info(f"Result: {result}")
    else:
        try:
            autoscaler.start()
        except KeyboardInterrupt:
            logger.info("Stopping autoscaler...")
            autoscaler.stop()


if __name__ == "__main__":
    main()
