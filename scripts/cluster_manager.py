#!/usr/bin/env python3
"""
Ray Cluster & Services Manager

This script provides a comprehensive management interface for the Ray cluster
and all associated services. It handles the complete lifecycle including
shutdown, restart, and health checking.
"""

import argparse
import logging
import subprocess
import sys
import time
import os
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def run_command(command: str, cwd: Optional[str] = None, capture_output: bool = True) -> subprocess.CompletedProcess:
    """
    Run a shell command and return the result.

    Args:
        command: Command to run
        cwd: Working directory
        capture_output: Whether to capture output

    Returns:
        CompletedProcess result
    """
    logger.info(f"Running: {command}")
    
    if cwd:
        logger.info(f"Working directory: {cwd}")
    
    result = subprocess.run(
        command, 
        shell=True, 
        capture_output=capture_output, 
        text=True,
        cwd=cwd
    )
    
    if capture_output:
        logger.debug(f"Return code: {result.returncode}")
        if result.stdout:
            logger.debug(f"STDOUT: {result.stdout}")
        if result.stderr:
            logger.debug(f"STDERR: {result.stderr}")
    
    return result


def check_docker_running() -> bool:
    """Check if Docker is running."""
    try:
        result = run_command("docker info")
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Error checking Docker: {e}")
        return False


def check_containers_status() -> Dict[str, bool]:
    """Check the status of Ray cluster containers."""
    try:
        result = run_command("docker ps --format '{{.Names}}'")
        running_containers = result.stdout.strip().split('\n') if result.stdout.strip() else []
        
        return {
            "ray-head": "ray-head" in running_containers,
            "ray-worker-1": "ray-worker-1" in running_containers,
            "ray-worker-2": "ray-worker-2" in running_containers,
        }
    except Exception as e:
        logger.error(f"Error checking container status: {e}")
        return {}


def check_services_health() -> Dict[str, bool]:
    """Check if Ray Serve services are responding."""
    endpoints = {
        "main": "http://localhost:8000/health",
        "algorunner": "http://localhost:8000/api/algorunner/status",
        "screener": "http://localhost:8000/api/screener/status", 
        "tickscrawler": "http://localhost:8000/api/tickscrawler/status"
    }
    
    status = {}
    
    for service, url in endpoints.items():
        try:
            result = run_command(f"curl -s -o /dev/null -w '%{{http_code}}' {url}")
            status[service] = result.stdout.strip() == "200"
        except Exception as e:
            logger.debug(f"Health check failed for {service}: {e}")
            status[service] = False
    
    return status


def shutdown_services() -> bool:
    """Shutdown Ray Serve services cleanly."""
    logger.info("Shutting down Ray Serve services...")
    
    try:
        # Try to shutdown services via the serve_app shutdown command
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        
        result = run_command(
            "docker exec ray-head python /workspace/serve_app/serve_app.py shutdown",
            cwd=project_root
        )
        
        if result.returncode == 0:
            logger.info("Ray Serve services shut down cleanly")
            return True
        else:
            logger.warning("Service shutdown command failed, services may still be running")
            return False
            
    except Exception as e:
        logger.error(f"Error shutting down services: {e}")
        return False


def shutdown_cluster() -> bool:
    """Shutdown the Ray cluster containers."""
    logger.info("Shutting down Ray cluster...")
    
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        
        result = run_command("python scripts/start_cluster.py stop", cwd=project_root)
        
        if result.returncode == 0:
            logger.info("Ray cluster shut down successfully")
            return True
        else:
            logger.error("Failed to shutdown Ray cluster")
            return False
            
    except Exception as e:
        logger.error(f"Error shutting down cluster: {e}")
        return False


def start_cluster(num_workers: int = 2, with_services: bool = True) -> bool:
    """Start the Ray cluster."""
    logger.info(f"Starting Ray cluster with {num_workers} workers...")
    
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        
        cmd = f"python scripts/start_cluster.py start --num-workers {num_workers}"
        if with_services:
            cmd += " --with-services"
        
        result = run_command(cmd, cwd=project_root)
        
        if result.returncode == 0:
            logger.info("Ray cluster started successfully")
            return True
        else:
            logger.error("Failed to start Ray cluster")
            return False
            
    except Exception as e:
        logger.error(f"Error starting cluster: {e}")
        return False


def deploy_services() -> bool:
    """Deploy Ray Serve services to the running cluster."""
    logger.info("Deploying Ray Serve services...")
    
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        
        result = run_command("python scripts/start_cluster.py deploy", cwd=project_root)
        
        if result.returncode == 0:
            logger.info("Ray Serve services deployed successfully")
            return True
        else:
            logger.error("Failed to deploy Ray Serve services")
            return False
            
    except Exception as e:
        logger.error(f"Error deploying services: {e}")
        return False


def full_shutdown() -> bool:
    """Perform a complete shutdown of services and cluster."""
    logger.info("Performing full system shutdown...")
    
    success = True
    
    # Step 1: Shutdown services
    if not shutdown_services():
        logger.warning("Service shutdown had issues, continuing...")
        success = False
    
    # Step 2: Shutdown cluster
    if not shutdown_cluster():
        logger.error("Cluster shutdown failed")
        success = False
    
    # Step 3: Force cleanup if needed
    containers = check_containers_status()
    running_containers = [name for name, running in containers.items() if running]
    
    if running_containers:
        logger.warning(f"Containers still running: {running_containers}")
        logger.info("Attempting force cleanup...")
        
        for container in running_containers:
            try:
                run_command(f"docker stop {container}")
                run_command(f"docker rm {container}")
            except Exception as e:
                logger.error(f"Failed to force stop {container}: {e}")
                success = False
    
    if success:
        logger.info("Full shutdown completed successfully")
    else:
        logger.warning("Shutdown completed with some issues")
    
    return success


def full_restart(num_workers: int = 2) -> bool:
    """Perform a complete restart of the entire system."""
    logger.info("Performing full system restart...")
    
    # Step 1: Full shutdown
    logger.info("Step 1: Shutting down current system...")
    full_shutdown()
    
    # Step 2: Wait a moment for cleanup
    logger.info("Waiting for cleanup...")
    time.sleep(3)
    
    # Step 3: Start cluster with services
    logger.info("Step 2: Starting fresh cluster with services...")
    if start_cluster(num_workers=num_workers, with_services=True):
        logger.info("Full restart completed successfully")
        return True
    else:
        logger.error("Full restart failed during startup")
        return False


def show_status() -> None:
    """Show comprehensive system status."""
    print("\n=== System Status ===")
    
    # Docker status
    docker_ok = check_docker_running()
    print(f"Docker: {'Running' if docker_ok else 'Not running'}")
    
    if not docker_ok:
        print("Docker is not running. Please start Docker first.")
        return
    
    # Container status
    containers = check_containers_status()
    print("\nContainers:")
    for name, running in containers.items():
        status = "Running" if running else "Stopped"
        print(f"  {name}: {status}")
    
    # Check if any containers are running
    any_running = any(containers.values())
    
    if any_running:
        # Service health
        print("\nServices:")
        services = check_services_health()
        for name, healthy in services.items():
            status = "Healthy" if healthy else "Unhealthy"
            print(f"  {name}: {status}")
        
        # Connection info
        print("\n=== Connection Information ===")
        print("Ray Client: ray://localhost:10000 (from host)")
        print("Ray Dashboard: http://localhost:8265")
        print("API Endpoints: http://localhost:8000")
        print("  • Health: http://localhost:8000/health")
        print("  • Algorunner: http://localhost:8000/api/algorunner/")
        print("  • Screener: http://localhost:8000/api/screener/")
        print("  • Tickscrawler: http://localhost:8000/api/tickscrawler/")
    else:
        print("\nNo containers are running. Use 'start' or 'restart' to begin.")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Ray Cluster & Services Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s status                    # Show system status
  %(prog)s start                     # Start cluster with services
  %(prog)s start --no-services       # Start cluster without services
  %(prog)s deploy                    # Deploy services to running cluster
  %(prog)s shutdown                  # Shutdown services only
  %(prog)s stop                      # Stop entire cluster
  %(prog)s restart                   # Full restart (shutdown + start)
  %(prog)s restart --workers 1       # Restart with 1 worker
        """
    )
    
    parser.add_argument(
        "action",
        choices=["start", "stop", "restart", "shutdown", "deploy", "status"],
        help="Action to perform"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="Number of worker nodes (default: 2)"
    )
    
    parser.add_argument(
        "--no-services",
        action="store_true",
        help="Start cluster without automatically deploying services"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Check Docker first
    if args.action != "status" and not check_docker_running():
        logger.error("Docker is not running. Please start Docker first.")
        sys.exit(1)
    
    try:
        if args.action == "status":
            show_status()
            
        elif args.action == "start":
            with_services = not args.no_services
            if start_cluster(num_workers=args.workers, with_services=with_services):
                show_status()
            else:
                sys.exit(1)
                
        elif args.action == "stop":
            if not full_shutdown():
                sys.exit(1)
                
        elif args.action == "shutdown":
            if not shutdown_services():
                sys.exit(1)
                
        elif args.action == "deploy":
            if not deploy_services():
                sys.exit(1)
                
        elif args.action == "restart":
            if full_restart(num_workers=args.workers):
                show_status()
            else:
                sys.exit(1)
                
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
