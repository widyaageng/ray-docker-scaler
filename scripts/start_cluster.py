#!/usr/bin/env python3
"""
Ray Cluster Startup Script (Containerized)

This script starts a Ray cluster using Docker containers for local development and testing.
"""

import argparse
import os
import sys
import time
import logging
import subprocess
from typing import Dict, Any, Optional,Literal

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_infra_command(command: str, **kwargs) -> bool:
    """
    Run an infrastructure command via infra.py.

    Args:
        command: The infra.py command to run
        **kwargs: Additional arguments

    Returns:
        True if successful, False otherwise
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        infra_script = os.path.join(script_dir, "infra.py")

        cmd_args = ["python", infra_script, command]

        # Add optional arguments
        for key, value in kwargs.items():
            if value is not None:
                cmd_args.append(f"--{key.replace('_', '-')}")
                if value is not True:  # Don't add value for boolean flags
                    cmd_args.append(str(value))

        logger.info(f"Running: {' '.join(cmd_args)}")
        result = subprocess.run(cmd_args, check=True)
        return result.returncode == 0

    except subprocess.CalledProcessError as e:
        logger.error(f"Infrastructure command failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to run infrastructure command: {e}")
        return False


def start_ray_cluster(
    num_workers: int = 2,
    num_cpus: Optional[int] = None,
    num_gpus: Optional[int] = None,
    object_store_memory: str = "1GB",
) -> bool:
    """
    Start Ray cluster using Docker containers.

    Args:
        num_workers: Number of worker nodes
        num_cpus: Number of CPUs per node
        num_gpus: Number of GPUs per node
        object_store_memory: Object store memory limit

    Returns:
        True if successful, False otherwise
    """
    logger.info("Starting Ray cluster in Docker containers...")

    kwargs = {"num_workers": num_workers, "object_store_memory": object_store_memory}

    if num_cpus is not None:
        kwargs["num_cpus"] = num_cpus
    if num_gpus is not None:
        kwargs["num_gpus"] = num_gpus

    return run_infra_command("start-ray", **kwargs)


def stop_ray_cluster() -> bool:
    """Stop Ray cluster containers."""
    logger.info("Stopping Ray cluster...")
    return run_infra_command("stop-ray")


def restart_ray_cluster(
    num_workers: int = 2,
    num_cpus: Optional[int] = None,
    num_gpus: Optional[int] = None,
    object_store_memory: str = "1GB",
) -> bool:
    """Restart Ray cluster containers."""
    logger.info("Restarting Ray cluster...")

    kwargs = {"num_workers": num_workers, "object_store_memory": object_store_memory}

    if num_cpus is not None:
        kwargs["num_cpus"] = num_cpus
    if num_gpus is not None:
        kwargs["num_gpus"] = num_gpus

    return run_infra_command("restart-ray", **kwargs)


def get_cluster_status() -> Dict[str, Any]:
    """Get Ray cluster status via infra.py."""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        infra_script = os.path.join(script_dir, "infra.py")

        result = subprocess.run(
            ["python", infra_script, "ray-status"],
            capture_output=True,
            text=True,
            check=True,
        )

        return {
            "status": "running" if result.returncode == 0 else "error",
            "output": result.stdout,
        }

    except subprocess.CalledProcessError as e:
        return {
            "status": "error",
            "error": str(e),
            "output": e.stdout if hasattr(e, "stdout") else "",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def action_serve_app(
        action: Literal["deploy", "shutdown"] = "deploy",
        address: str = "auto",
        serve_host: str = "0.0.0.0",
        serve_port: int = 8000,
) -> bool:
    """
    Deploy the Ray Serve application to the running cluster.
    
    Args:
        address: Ray cluster address (default is 'auto')
        action: Action to perform ('deploy' or 'shutdown')
        serve_host: Host for Ray Serve (default is '0.0.0.0')
        serve_port: Port for Ray Serve (default is 8000)

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Actioning {action} on Ray Serve application to cluster...")
        
        # Execute deployment inside the head node container
        result = subprocess.run([
            "docker", "exec", "ray-head",
            "python", "/workspace/serve_app/serve_app.py", action,
            "--address", address,
            "--serve-host", serve_host,
            "--serve-port", str(serve_port)
        ], capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            logger.info(f"Ray Serve application action:{action} successfully")
            if action == "deploy":
                logger.info("Service endpoints:")
                logger.info(f"   • Main API: http://localhost:{serve_port}/")
                logger.info(f"   • Health check: http://localhost:{serve_port}/health")
                logger.info(f"   • Algorunner: http://localhost:{serve_port}/api/algorunner/")
                logger.info(f"   • Screener: http://localhost:{serve_port}/api/screener/")
                logger.info(f"   • Tickscrawler: http://localhost:{serve_port}/api/tickscrawler/")
            return True
        else:
            logger.error(f"Failed to {action} Ray Serve application")
            logger.error(f"Return code: {result.returncode}")
            if result.stdout:
                logger.error(f"STDOUT: {result.stdout}")
            if result.stderr:
                logger.error(f"STDERR: {result.stderr}")
            return False
        
    except Exception as e:
        logger.error(f"Failed to {action} Ray Serve application: {e}")
        return False


def connect_to_ray_cluster(address: str = "ray://localhost:10000") -> bool:
    """
    Test Ray cluster connectivity (executed inside container).

    Args:
        address: Ray cluster address (not used, test runs inside container)

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Testing Ray cluster connectivity...")
        
        # Test Ray status from inside the container
        result = subprocess.run([
            "docker", "exec", "ray-head",
            "ray", "status"
        ], capture_output=True, text=True, check=False)
        
        if result.returncode == 0:
            logger.info("Ray cluster is accessible and running")
            if result.stdout:
                # Show a summary instead of full output
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'Active:' in line or 'CPU' in line or 'memory' in line:
                        logger.info(f"  {line.strip()}")
            return True
        else:
            logger.error("Failed to access Ray cluster")
            if result.stderr:
                logger.error(f"Error: {result.stderr}")
            return False

    except Exception as e:
        logger.error(f"Failed to test Ray cluster connectivity: {e}")
        return False


def show_cluster_info() -> None:
    """Show cluster connection information."""
    print("\n=== Ray Cluster Information ===")
    print("Container Network: ray-cluster")
    print("Ray Client Address: ray://localhost:10000 (from host)")
    print("Ray Dashboard: http://localhost:8265")
    print("Ray Serve API: http://localhost:8000")
    print("\nTo connect from Python:")
    print("  import ray")
    print("  ray.init(address='ray://localhost:10000')  # From host")
    print("  ray.init(address='ray://0.0.0.0:10000')   # From inside container")
    print()
    print("Note: Ray head node binds to 0.0.0.0 inside container for external access")


def parse_memory_string(memory_str: str) -> str:
    """
    Parse and validate memory string (e.g., '2GB', '512MB').

    Args:
        memory_str: Memory string

    Returns:
        Validated memory string
    """
    memory_str = memory_str.upper()

    if not (
        memory_str.endswith("GB")
        or memory_str.endswith("MB")
        or memory_str.endswith("KB")
    ):
        # Assume bytes if no unit specified
        try:
            int(memory_str)
            return memory_str
        except ValueError:
            raise ValueError(f"Invalid memory format: {memory_str}")

    return memory_str


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Ray Cluster Startup Script (Containerized)"
    )
    parser.add_argument(
        "mode",
        choices=[
            "start",
            "stop",
            "restart",
            "status",
            "connect",
            "info",
            "serve-deploy-start",
            "serve-deploy-shutdown",
        ],

        help="Cluster operation mode",
    )
    parser.add_argument(
        "--address",
        type=str,
        default="0.0.0.0:10000",
        help="Ray cluster address for connect/deploy mode (default: 0.0.0.0:10000)",
    )
    parser.add_argument(
        "--num-workers", type=int, default=2, help="Number of worker nodes (default: 2)"
    )
    parser.add_argument("--num-cpus", type=float, help="Number of CPUs per node")
    parser.add_argument("--num-gpus", type=float, help="Number of GPUs per node")
    parser.add_argument(
        "--object-store-memory",
        type=str,
        default="1GB",
        help="Object store memory limit per node (e.g., '1GB', '256MB')",
    )
    parser.add_argument(
        "--keep-alive",
        action="store_true",
        help="Keep monitoring the cluster (don't exit)",
    )
    parser.add_argument(
        "--with-services",
        action="store_true",
        help="Deploy Ray Serve services after starting the cluster",
    )

    args = parser.parse_args()

    # Validate memory format
    try:
        _ = parse_memory_string(args.object_store_memory)
    except ValueError as e:
        logger.error(f"Invalid memory format: {e}")
        sys.exit(1)

    if args.mode == "start":
        logger.info("Starting Ray cluster...")
        if start_ray_cluster(
            num_workers=args.num_workers,
            num_cpus=args.num_cpus,
            num_gpus=args.num_gpus,
            object_store_memory=args.object_store_memory,
        ):
            show_cluster_info()
            
            # Deploy services if requested
            if args.with_services:
                logger.info("Deploying Ray Serve services...")
                time.sleep(10)  # Wait for cluster to stabilize
                if not action_serve_app(
                    action="deploy",
                    address=args.address,
                    serve_host="0.0.0.0",
                    serve_port=8000,
                ):
                    logger.error("Service deployment failed, but cluster is running")

            if args.keep_alive:
                logger.info("Ray cluster is running. Press Ctrl+C to stop.")
                try:
                    while True:
                        time.sleep(10)
                        # Optionally check cluster health
                        status = get_cluster_status()
                        if status.get("status") != "running":
                            logger.warning("Cluster appears to be unhealthy")
                except KeyboardInterrupt:
                    logger.info("Shutting down...")
                    stop_ray_cluster()
        else:
            sys.exit(1)

    elif args.mode == "stop":
        logger.info("Stopping Ray cluster...")
        if not stop_ray_cluster():
            sys.exit(1)

    elif args.mode == "restart":
        logger.info("Restarting Ray cluster...")
        if restart_ray_cluster(
            num_workers=args.num_workers,
            num_cpus=args.num_cpus,
            num_gpus=args.num_gpus,
            object_store_memory=args.object_store_memory,
        ):
            show_cluster_info()
            
            # Deploy services if requested
            if args.with_services:
                logger.info("Deploying Ray Serve services...")
                time.sleep(10)  # Wait for cluster to stabilize
                if not action_serve_app(
                    action="deploy",
                    address=args.address,
                    serve_host="0.0.0.0",
                    serve_port=8000,
                ):
                    logger.error("Service deployment failed, but cluster is running")
        else:
            sys.exit(1)

    elif args.mode == "status":
        logger.info("Getting cluster status...")
        status = get_cluster_status()

        print(f"Cluster Status: {status.get('status', 'unknown')}")
        if status.get("output"):
            print(status["output"])
        if status.get("error"):
            print(f"Error: {status['error']}")

    elif args.mode == "connect":
        logger.info("Connecting to Ray cluster...")
        if connect_to_ray_cluster(args.address):
            if args.keep_alive:
                logger.info("Connected to Ray cluster. Press Ctrl+C to disconnect.")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Disconnecting...")
                    import ray

                    ray.shutdown()
        else:
            sys.exit(1)

    elif args.mode == "info":
        show_cluster_info()

    elif args.mode == "serve-deploy-start":
        logger.info("Deploying Ray Serve services to existing cluster...")
        if not action_serve_app(
            "deploy",
            address=args.address,
            serve_host="0.0.0.0",
            serve_port=8000,
        ):
            sys.exit(1)
    elif args.mode == "serve-deploy-shutdown":
        logger.info("Shutting down Ray Serve services...")
        if not action_serve_app(
            "shutdown",
            address=args.address,
            serve_host="0.0.0.0",
            serve_port=8000,
        ):
            sys.exit(1)


if __name__ == "__main__":
    main()
