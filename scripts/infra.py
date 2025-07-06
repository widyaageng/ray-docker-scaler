#!/usr/bin/env python3
"""
Infrastructure Management Script

This script manages the Docker infrastructure for the Ray cluster.
"""

from typing import Optional

import argparse
import subprocess
import sys
import os
import time
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# CONSTANTS
RAY_IMAGE_VERSION = "rayproject/ray:2.47.1.aeaf41-py39-cpu"


def run_command(command: str, check: bool = True) -> subprocess.CompletedProcess:
    """
    Run a shell command and return the result.

    Args:
        command: Command to run
        check: Whether to check return code

    Returns:
        CompletedProcess result
    """
    logger.info(f"Running: {command}")
    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if check and result.returncode != 0:
        logger.error(f"Command failed with code {result.returncode}")
        logger.error(f"STDOUT: {result.stdout}")
        logger.error(f"STDERR: {result.stderr}")
        sys.exit(1)

    return result


def check_docker() -> bool:
    """Check if Docker and Docker Compose are available."""
    try:
        run_command("docker --version")
        run_command("docker compose version")
        return True
    except SystemExit:
        logger.error("Docker or Docker Compose not found. Please install Docker.")
        return False


def ensure_ray_network() -> bool:
    """Ensure the ray-cluster network exists."""
    try:
        # Check if network exists
        result = run_command(
            "docker network ls --filter name=ray-cluster --format '{{.Name}}'",
            check=False,
        )
        if "ray-cluster" not in result.stdout:
            logger.info("Creating ray-cluster network...")
            run_command("docker network create ray-cluster")
            logger.info("Ray cluster network created")
        else:
            logger.info("Ray cluster network already exists")
        return True
    except Exception as e:
        logger.error(f"Failed to ensure ray-cluster network: {e}")
        return False


def parse_memory_string(memory_str: str) -> int:
    """
    Parse memory string (e.g., '2GB', '512MB') to bytes.

    Args:
        memory_str: Memory string

    Returns:
        Memory in bytes
    """
    memory_str = memory_str.upper()

    if memory_str.endswith("GB"):
        return int(float(memory_str[:-2]) * 1024 * 1024 * 1024)
    elif memory_str.endswith("MB"):
        return int(float(memory_str[:-2]) * 1024 * 1024)
    elif memory_str.endswith("KB"):
        return int(float(memory_str[:-2]) * 1024)
    else:
        return int(memory_str)


def start_ray_head(
    num_cpus: Optional[int] = None,
    num_gpus: Optional[int] = None,
    object_store_memory: str = "1GB",
) -> bool:
    """Start Ray head node in Docker container."""
    try:
        logger.info("Starting Ray head node container...")

        # Ensure network exists
        if not ensure_ray_network():
            return False

        # Create logs directory
        run_command("mkdir -p logs")

        # Parse memory string to bytes
        object_store_bytes = parse_memory_string(object_store_memory)

        # Build environment variables
        env_vars = []
        if num_cpus:
            env_vars.append(f"-e RAY_NUM_CPUS={num_cpus}")
        if num_gpus:
            env_vars.append(f"-e RAY_NUM_GPUS={num_gpus}")

        env_vars_str = " ".join(env_vars)

        # Start Ray head container
        command = f"""
        docker run -d \\
            --name ray-head \\
            --network ray-cluster \\
            --shm-size=2gb \\
            --init \\
            -p 10000:10000 \\
            -p 10001:10001 \\
            -p 8265:8265 \\
            -p 8000:8000 \\
            -v $(pwd):/workspace \\
            -v $(pwd)/logs:/tmp/ray \\
            -w /workspace \\
            {env_vars_str} \\
            -e RAY_HEAD_NODE=true \\
            -e RAY_DISABLE_IMPORT_WARNING=1 \\
            {RAY_IMAGE_VERSION} \\
            bash -c 'RAY_DISABLE_IMPORT_WARNING=1 ray start --head --node-ip-address=$(hostname -I) --port=10000 --ray-client-server-port=10001 --dashboard-host=0.0.0.0 --dashboard-port=8265 --include-dashboard=true --disable-usage-stats --object-store-memory={object_store_bytes} --num-cpus=1 && sleep infinity'
        """

        run_command(command.replace("\n", " ").replace("\\", ""))

        # Wait for head node to be ready
        logger.info("Waiting for Ray head node to be ready...")
        for i in range(30):
            result = run_command("docker exec ray-head ray status", check=False)
            if result.returncode == 0:
                logger.info("Ray head node is ready!")
                return True
            time.sleep(2)

        logger.error("Ray head node failed to start properly")
        return False

    except Exception as e:
        logger.error(f"Failed to start Ray head node: {e}")
        return False


def start_ray_workers(
    num_workers: int = 2,
    num_cpus: Optional[int] = None,
    num_gpus: Optional[int] = None,
    object_store_memory: str = "1GB",
) -> bool:
    """Start Ray worker nodes in Docker containers."""
    try:
        logger.info(f"Starting {num_workers} Ray worker node(s)...")

        # Parse memory string to bytes
        object_store_bytes = parse_memory_string(object_store_memory)

        for i in range(num_workers):
            worker_name = f"ray-worker-{i+1}"

            # Build environment variables
            env_vars = []
            if num_cpus:
                env_vars.append(f"-e RAY_NUM_CPUS={num_cpus}")
            if num_gpus:
                env_vars.append(f"-e RAY_NUM_GPUS={num_gpus}")

            env_vars_str = " ".join(env_vars)

            # Start worker container
            command = f"""
            docker run -d \\
                --name {worker_name} \\
                --network ray-cluster \\
                --shm-size=2gb \\
                --init \\
                -v $(pwd):/workspace \\
                -v $(pwd)/logs:/tmp/ray \\
                -w /workspace \\
                {env_vars_str} \\
                -e RAY_HEAD_ADDRESS=ray-head:10000 \\
                -e RAY_DISABLE_IMPORT_WARNING=1 \\
                {RAY_IMAGE_VERSION} \\
                bash -c 'sleep 10 && RAY_DISABLE_IMPORT_WARNING=1 ray start --address=ray-head:10000 --object-store-memory={object_store_bytes} --num-cpus=1 --disable-usage-stats && sleep infinity'
            """

            run_command(command.replace("\n", " ").replace("\\", ""))
            logger.info(f"Started {worker_name}")

        # Wait for workers to connect
        logger.info("Waiting for workers to connect...")
        time.sleep(10)

        # Check cluster status
        result = run_command("docker exec ray-head ray status", check=False)
        if result.returncode == 0:
            logger.info("Ray workers started successfully!")
            logger.info(f"Cluster status:\n{result.stdout}")
            return True
        else:
            logger.error("Some workers failed to connect")
            return False

    except Exception as e:
        logger.error(f"Failed to start Ray workers: {e}")
        return False

def get_next_worker_index() -> int:
    """Get the next available worker index."""
    try:
        result = run_command(
            "docker ps --filter name=ray-worker --format '{{.Names}}'", check=False
        )
        worker_names = [w for w in result.stdout.strip().split("\n") if w.strip() and w.startswith("ray-worker-")]
        
        if not worker_names:
            return 1
        
        # Extract indices and find the highest
        indices = []
        for name in worker_names:
            try:
                index = int(name.split("-")[-1])
                indices.append(index)
            except ValueError:
                continue
        
        return max(indices) + 1 if indices else 1
    
    except Exception as e:
        logger.error(f"Failed to get next worker index: {e}")
        return 1


def get_ray_cluster_metrics() -> dict:
    """Get Ray cluster metrics including pending tasks."""
    try:
        # Get Ray status with detailed information
        result = run_command("docker exec ray-head ray status --verbose", check=False)
        if result.returncode != 0:
            return {"status": "error", "error": "Ray not responding"}
        
        status_output = result.stdout
        
        # Parse the status output to extract metrics
        metrics = {
            "pending_tasks": 0,
            "running_tasks": 0,
            "total_cpus": 0,
            "used_cpus": 0,
            "total_memory": 0,
            "used_memory": 0,
            "nodes": 0
        }
        
        # Extract pending tasks from Ray status
        lines = status_output.split('\n')
        for line in lines:
            line = line.strip()
            if "pending tasks" in line.lower():
                try:
                    # Extract number from patterns like "10 pending tasks"
                    import re
                    match = re.search(r'(\d+)\s+pending\s+tasks', line, re.IGNORECASE)
                    if match:
                        metrics["pending_tasks"] = int(match.group(1))
                except:
                    pass
            elif "running tasks" in line.lower():
                try:
                    import re
                    match = re.search(r'(\d+)\s+running\s+tasks', line, re.IGNORECASE)
                    if match:
                        metrics["running_tasks"] = int(match.group(1))
                except:
                    pass
            elif "CPU" in line and "Memory" in line:
                try:
                    # Parse resource lines
                    import re
                    cpu_match = re.search(r'(\d+\.?\d*)/(\d+\.?\d*)\s+CPU', line)
                    if cpu_match:
                        metrics["used_cpus"] = float(cpu_match.group(1)) #type: ignore
                        metrics["total_cpus"] = float(cpu_match.group(2)) #type: ignore
                except:
                    pass
        
        # Get node count
        result = run_command("docker exec ray-head ray status --address=auto | grep -c 'NodeID'", check=False)
        if result.returncode == 0:
            try:
                metrics["nodes"] = int(result.stdout.strip())
            except:
                pass
        
        return metrics
    
    except Exception as e:
        logger.error(f"Failed to get Ray cluster metrics: {e}")
        return {"status": "error", "error": str(e)}


def start_additional_ray_worker(
    num_cpus: Optional[int] = None,
    num_gpus: Optional[int] = None,
    object_store_memory: str = "1GB",
) -> bool:
    """Start an additional Ray worker with the next available index."""
    try:
        # Get next worker index
        worker_index = get_next_worker_index()
        worker_name = f"ray-worker-{worker_index}"
        
        logger.info(f"Starting additional Ray worker: {worker_name}")
        
        # Parse memory string to bytes
        object_store_bytes = parse_memory_string(object_store_memory)
        
        # Build environment variables
        env_vars = []
        if num_cpus:
            env_vars.append(f"-e RAY_NUM_CPUS={num_cpus}")
        if num_gpus:
            env_vars.append(f"-e RAY_NUM_GPUS={num_gpus}")
        
        env_vars_str = " ".join(env_vars)
        
        # Start worker container
        command = f"""
        docker run -d \\
            --name {worker_name} \\
            --network ray-cluster \\
            --shm-size=2gb \\
            --init \\
            -v $(pwd)/..:/workspace \\
            -v $(pwd)/../logs:/tmp/ray \\
            -w /workspace \\
            {env_vars_str} \\
            -e RAY_HEAD_ADDRESS=ray-head:10000 \\
            -e RAY_DISABLE_IMPORT_WARNING=1 \\
            {RAY_IMAGE_VERSION} \\
            bash -c 'sleep 10 && RAY_DISABLE_IMPORT_WARNING=1 ray start --address=ray-head:10000 --object-store-memory={object_store_bytes} --num-cpus=1 --disable-usage-stats && sleep infinity'
        """
        # command = f"""
        # docker run -d \\
        #     --name {worker_name} \\
        #     --network ray-cluster \\
        #     --shm-size=2gb \\
        #     --init \\
        #     -v $(pwd):/workspace \\
        #     -v $(pwd)/logs:/tmp/ray \\
        #     -w /workspace \\
        #     {env_vars_str} \\
        #     -e RAY_HEAD_ADDRESS=ray-head:10000 \\
        #     -e RAY_DISABLE_IMPORT_WARNING=1 \\
        #     {RAY_IMAGE_VERSION} \\
        #     bash -c 'sleep 5 && RAY_DISABLE_IMPORT_WARNING=1 ray start --address=ray-head:10000 --object-store-memory={object_store_bytes} --num-cpus=1 --disable-usage-stats && sleep infinity'
        # """
        
        run_command(command.replace("\n", " ").replace("\\", ""))
        
        # Wait for worker to connect
        logger.info(f"Waiting for {worker_name} to connect...")
        time.sleep(10)
        
        # Verify connection
        result = run_command("docker exec ray-head ray status", check=False)
        if result.returncode == 0:
            logger.info(f"Successfully started {worker_name}")
            return True
        else:
            logger.error(f"Failed to connect {worker_name}")
            return False
    
    except Exception as e:
        logger.error(f"Failed to start additional Ray worker: {e}")
        return False


def start_ray_watcher(
    check_interval: int = 120,  # 2 minutes
    pending_task_threshold: int = 0,  # Number of pending tasks to trigger scaling
    max_workers: int = 10,  # Maximum number of workers
    scale_up_cooldown: int = 300,  # 5 minutes cooldown between scale-ups
) -> bool:
    """Start Ray watcher service to monitor Ray cluster and auto-scale workers."""
    try:
        logger.info("Starting Ray watcher service...")
        
        # Ensure network exists
        if not ensure_ray_network():
            return False
        
        # Get the path to the watcher script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        watcher_script_path = os.path.join(script_dir, "ray_watcher.py")
        
        # Check if watcher script exists
        if not os.path.exists(watcher_script_path):
            logger.error(f"Watcher script not found at {watcher_script_path}")
            return False
        
        # Start watcher container with environment variables for configuration
        command = f"""
        docker run -d \\
            --name ray-watcher \\
            --network ray-cluster \\
            --init \\
            -v $(pwd):/workspace \\
            -v $(pwd)/logs:/tmp/ray \\
            -w /workspace \\
            -e WATCHER_CHECK_INTERVAL={check_interval} \\
            -e WATCHER_PENDING_THRESHOLD={pending_task_threshold} \\
            -e WATCHER_MAX_WORKERS={max_workers} \\
            -e WATCHER_COOLDOWN={scale_up_cooldown} \\
            -e RAY_HEAD_ADDRESS=ray-head:10000 \\
            -e RAY_DISABLE_IMPORT_WARNING=1 \\
            {RAY_IMAGE_VERSION} \\
            bash -c 'export PATH=$PATH:/workspace && python /workspace/scripts/ray_watcher.py'
            
        """
        
        run_command(command.replace("\n", " ").replace("\\", ""))
        
        logger.info("Ray watcher service started successfully")
        logger.info(f"Monitoring interval: {check_interval} seconds")
        logger.info(f"Pending task threshold: {pending_task_threshold}")
        logger.info(f"Maximum workers: {max_workers}")
        logger.info(f"Scale-up cooldown: {scale_up_cooldown} seconds")
        return True
    
    except Exception as e:
        logger.error(f"Failed to start Ray watcher service: {e}")
        return False


def stop_ray_watcher() -> bool:
    """Stop Ray watcher service."""
    try:
        logger.info("Stopping Ray watcher service...")
        run_command("docker stop ray-watcher", check=False)
        run_command("docker rm ray-watcher", check=False)
        logger.info("Ray watcher service stopped")
        return True
    except Exception as e:
        logger.error(f"Failed to stop Ray watcher service: {e}")
        return False

def stop_ray_cluster() -> bool:
    """Stop all Ray containers."""
    try:
        logger.info("Stopping Ray cluster...")

        # Stop and remove Ray containers
        result = run_command(
            "docker ps --filter name=ray- --format '{{.Names}}'", check=False
        )
        ray_containers = (
            result.stdout.strip().split("\n") if result.stdout.strip() else []
        )

        for container in ray_containers:
            if container:
                logger.info(f"Stopping {container}...")
                run_command(f"docker stop {container}", check=False)
                run_command(f"docker rm {container}", check=False)

        logger.info("Ray cluster stopped")
        return True

    except Exception as e:
        logger.error(f"Failed to stop Ray cluster: {e}")
        return False


def get_ray_cluster_status() -> dict:
    """Get Ray cluster status."""
    try:
        # Check if head node exists
        result = run_command(
            "docker ps --filter name=ray-head --format '{{.Names}}'", check=False
        )
        if "ray-head" not in result.stdout:
            return {"status": "stopped", "head_running": False, "workers": 0}

        # Get Ray status from head node
        result = run_command("docker exec ray-head ray status", check=False)
        if result.returncode != 0:
            return {
                "status": "error",
                "head_running": True,
                "workers": 0,
                "error": "Ray not responding",
            }

        # Count worker containers
        result = run_command(
            "docker ps --filter name=ray-worker --format '{{.Names}}'", check=False
        )
        workers = len([w for w in result.stdout.strip().split("\n") if w.strip()])

        return {
            "status": "running",
            "head_running": True,
            "workers": workers,
            "ray_status": result.stdout,
        }

    except Exception as e:
        return {"status": "error", "error": str(e)}


def show_ray_logs(service: Optional[str] = None, follow: bool = False) -> None:
    """Show logs for Ray services."""
    try:
        if service:
            container_name = (
                f"ray-{service}" if service in ["head"] else f"ray-{service}"
            )
            if service.startswith("worker"):
                container_name = (
                    service if service.startswith("ray-worker") else f"ray-{service}"
                )
        else:
            # Show all Ray container logs
            result = run_command(
                "docker ps --filter name=ray- --format '{{.Names}}'", check=False
            )
            containers = [c for c in result.stdout.strip().split("\n") if c.strip()]

            if not containers:
                logger.info("No Ray containers running")
                return

            for container in containers:
                print(f"\n=== Logs for {container} ===")
                log_cmd = f"docker logs {container}"
                if follow:
                    log_cmd += " -f"
                run_command(log_cmd, check=False)
            return

        # Show specific container logs
        log_cmd = f"docker logs {container_name}"
        if follow:
            log_cmd += " -f"
        run_command(log_cmd, check=False)

    except Exception as e:
        logger.error(f"Failed to show Ray logs: {e}")


def start_infrastructure() -> bool:
    """Start the infrastructure services."""
    try:
        logger.info("Starting infrastructure services...")

        # Create necessary directories
        run_command("mkdir -p postgres/data postgres/pgadmin redis/data", check=False)

        # Set proper permissions (skip if permission denied)
        run_command("chmod 755 postgres/data redis/data", check=False)
        run_command("chmod +x postgres/init/01-init-database.sh", check=False)

        # Start services
        run_command("docker compose -f infra-docker-compose.yaml up -d")

        logger.info("Waiting for services to be healthy...")
        time.sleep(10)

        # Check service health
        postgres_healthy = check_postgres_health()
        # Redis not needed - Ray has its own internal Redis
        # redis_healthy = check_redis_health()

        if postgres_healthy:
            logger.info("All infrastructure services are healthy!")
            return True
        else:
            logger.error("Some services are not healthy")
            return False

    except Exception as e:
        logger.error(f"Failed to start infrastructure: {e}")
        return False


def stop_infrastructure() -> bool:
    """Stop the infrastructure services."""
    try:
        logger.info("Stopping infrastructure services...")
        run_command("docker compose -f infra-docker-compose.yaml down")
        logger.info("Infrastructure services stopped")
        return True
    except Exception as e:
        logger.error(f"Failed to stop infrastructure: {e}")
        return False


def restart_infrastructure() -> bool:
    """Restart the infrastructure services."""
    logger.info("Restarting infrastructure services...")
    stop_infrastructure()
    time.sleep(2)
    return start_infrastructure()


def check_postgres_health() -> bool:
    """Check PostgreSQL health."""
    try:
        result = run_command(
            "docker exec ray-postgres pg_isready -U rayuser -d raycluster", check=False
        )
        if result.returncode == 0:
            logger.info("PostgreSQL is healthy")
            return True
        else:
            logger.warning("PostgreSQL is not healthy")
            return False
    except Exception as e:
        logger.error(f"Error checking PostgreSQL health: {e}")
        return False


def check_redis_health() -> bool:
    """Check Redis health."""
    try:
        result = run_command(
            "docker exec ray-redis redis-cli --raw incr ping", check=False
        )
        if result.returncode == 0:
            logger.info("Redis is healthy")
            return True
        else:
            logger.warning("Redis is not healthy")
            return False
    except Exception as e:
        logger.error(f"Error checking Redis health: {e}")
        return False


def get_service_status() -> dict:
    """Get status of all infrastructure services."""
    try:
        result = run_command(
            "docker compose -f infra-docker-compose.yaml ps --format json", check=False
        )

        if result.returncode == 0:
            services = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    services.append(json.loads(line))

            status = {
                "services": services,
                "postgres_healthy": check_postgres_health(),
                # Redis not needed - Ray has its own internal Redis
                # "redis_healthy": True,  # Always true since we don't use external Redis
            }
            return status
        else:
            return {"error": "Failed to get service status"}

    except Exception as e:
        return {"error": str(e)}


def show_logs(service: str = None, follow: bool = False) -> None:  # type: ignore
    """Show logs for infrastructure services."""
    try:
        if service:
            command = f"docker compose -f infra-docker-compose.yaml logs"
            if follow:
                command += " -f"
            command += f" {service}"
        else:
            command = "docker compose -f infra-docker-compose.yaml logs"
            if follow:
                command += " -f"

        # Don't capture output for logs, let it stream to console
        subprocess.run(command, shell=True)

    except KeyboardInterrupt:
        logger.info("Log streaming stopped")
    except Exception as e:
        logger.error(f"Error showing logs: {e}")


def cleanup_infrastructure() -> bool:
    """Clean up infrastructure (remove containers and volumes)."""
    try:
        logger.warning("This will remove all containers, volumes, and data!")
        confirmation = input("Are you sure? (yes/no): ")

        if confirmation.lower() != "yes":
            logger.info("Cleanup cancelled")
            return False

        logger.info("Cleaning up infrastructure...")
        run_command(
            "docker compose -f infra-docker-compose.yaml down -v --remove-orphans"
        )
        run_command("docker volume prune -f")

        # Remove data directories
        run_command("rm -rf postgres/data/* redis/data/*", check=False)

        logger.info("Infrastructure cleanup completed")
        return True

    except Exception as e:
        logger.error(f"Failed to cleanup infrastructure: {e}")
        return False


def show_connection_info() -> None:
    """Show connection information for services."""
    print("\n=== Infrastructure Connection Information ===")
    print("\nPostgreSQL:")
    print("  Host: localhost")
    print("  Port: 5432")
    print("  Database: raycluster")
    print("  Username: rayuser")
    print("  Password: raypassword")
    print(
        "  Connection URL: postgresql://rayuser:raypassword@localhost:5432/raycluster"
    )

    print("\n# Redis not needed - Ray has its own internal Redis")

    print("\nAdmin Tools:")
    print("  pgAdmin: http://localhost:8080")
    print("    Email: admin@raycluster.com")
    print("    Password: admin")

    print("\nRay Cluster:")
    print("  Client Address: ray://localhost:10001")
    print("  Dashboard: http://localhost:8265")
    print("  Serve API: http://localhost:8000")
    print()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Infrastructure Management Script")
    parser.add_argument(
        "action",
        choices=[
            "start-infra",
            "stop-infra",
            "restart-infra",
            "status-infra",
            "logs-infra",
            "cleanup-infra",
            "info-infra",
            "start-ray",
            "stop-ray",
            "restart-ray",
            "status-ray",
            "logs-ray",
            "add-worker",
            "start-watcher",
            "stop-watcher",
            "watcher-status",
        ],
        help="Action to perform",
    )
    parser.add_argument(
        "--service",
        choices=[
            "postgres",
            "redis",
            "pgadmin",
            "redis-commander",
            "head",
            "worker-1",
            "worker-2",
        ],
        help="Specific service for logs action",
    )
    parser.add_argument(
        "--follow", action="store_true", help="Follow logs in real-time"
    )
    parser.add_argument(
        "--num-workers", type=int, default=2, help="Number of Ray worker nodes to start"
    )
    parser.add_argument("--num-cpus", type=float, help="Number of CPUs per Ray node")
    parser.add_argument("--num-gpus", type=float, help="Number of GPUs per Ray node")
    parser.add_argument(
        "--object-store-memory",
        type=str,
        default="1GB",
        help="Object store memory limit per Ray node",
    )
    # Watcher-specific arguments
    parser.add_argument(
        "--check-interval",
        type=int,
        default=120,
        help="Watcher check interval in seconds (default: 120)",
    )
    parser.add_argument(
        "--pending-threshold",
        type=int,
        default=5,
        help="Pending tasks threshold to trigger scaling (default: 5)",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="Maximum number of workers (default: 10)",
    )
    parser.add_argument(
        "--cooldown",
        type=int,
        default=300,
        help="Scale-up cooldown in seconds (default: 300)",
    )

    args = parser.parse_args()

    if not check_docker():
        sys.exit(1)

    if args.action == "start-infra":
        if start_infrastructure():
            show_connection_info()
        else:
            sys.exit(1)

    elif args.action == "stop-infra":
        if not stop_infrastructure():
            sys.exit(1)

    elif args.action == "restart-infra":
        if restart_infrastructure():
            show_connection_info()
        else:
            sys.exit(1)

    elif args.action == "status-infra":
        status = get_service_status()
        if "error" in status:
            logger.error(f"Error getting status: {status['error']}")
            sys.exit(1)

        print("\n=== Infrastructure Service Status ===")
        for service in status["services"]:
            state = service.get("State", "unknown")
            health = service.get("Health", "unknown")
            print(f"  {service['Service']}: {state} ({health})")

        print(f"\nHealth Checks:")
        print(f"  PostgreSQL: {'✓' if status['postgres_healthy'] else '✗'}")
        print(f"  Redis: {'✓' if status['redis_healthy'] else '✗'}")
        print()

    elif args.action == "logs-infra":
        show_logs(args.service, args.follow)

    elif args.action == "cleanup-infra":
        if not cleanup_infrastructure():
            sys.exit(1)

    elif args.action == "info-infra":
        show_connection_info()

    # Ray cluster actions
    elif args.action == "start-ray":
        if not ensure_ray_network():
            sys.exit(1)

        if start_ray_head(args.num_cpus, args.num_gpus, args.object_store_memory):
            if start_ray_workers(
                args.num_workers, args.num_cpus, args.num_gpus, args.object_store_memory
            ):
                logger.info("Ray cluster started successfully!")
                logger.info("Dashboard available at: http://localhost:8265")
                logger.info("Ray Serve available at: http://localhost:8000")
            else:
                sys.exit(1)
        else:
            sys.exit(1)

    elif args.action == "stop-ray":
        if not stop_ray_cluster():
            sys.exit(1)

    elif args.action == "restart-ray":
        logger.info("Restarting Ray cluster...")
        stop_ray_cluster()
        time.sleep(5)

        if not ensure_ray_network():
            sys.exit(1)

        if start_ray_head(args.num_cpus, args.num_gpus, args.object_store_memory):
            if start_ray_workers(
                args.num_workers, args.num_cpus, args.num_gpus, args.object_store_memory
            ):
                logger.info("Ray cluster restarted successfully!")
            else:
                sys.exit(1)
        else:
            sys.exit(1)

    elif args.action == "status-ray":
        status = get_ray_cluster_status()
        print("\n=== Ray Cluster Status ===")
        print(f"  Status: {status['status']}")
        print(f"  Head Node: {'✓' if status.get('head_running') else '✗'}")
        print(f"  Workers: {status.get('workers', 0)}")

        if status.get("ray_status"):
            print(f"\nRay Status Output:")
            print(status["ray_status"])

        if status.get("error"):
            print(f"  Error: {status['error']}")
        print()

    elif args.action == "logs-ray":
        show_ray_logs(args.service, args.follow)

    elif args.action == "add-worker":
        logger.info("Adding new Ray worker...")
        if start_additional_ray_worker(args.num_cpus, args.num_gpus, args.object_store_memory):
            logger.info("Ray worker added successfully!")
        else:
            logger.error("Failed to add Ray worker")
            sys.exit(1)

    elif args.action == "start-watcher":
        logger.info("Starting Ray watcher service...")
        if start_ray_watcher(
            args.check_interval,
            args.pending_threshold,
            args.max_workers,
            args.cooldown,
        ):
            logger.info("Ray watcher service started successfully!")
        else:
            logger.error("Failed to start Ray watcher service")
            sys.exit(1)

    elif args.action == "stop-watcher":
        logger.info("Stopping Ray watcher service...")
        if stop_ray_watcher():
            logger.info("Ray watcher service stopped successfully!")
        else:
            logger.error("Failed to stop Ray watcher service")
            sys.exit(1)

    elif args.action == "watcher-status":
        # Check if watcher is running
        result = run_command("docker ps --filter name=ray-watcher --format '{{.Names}}'", check=False)
        if result and "ray-watcher" in result.stdout:
            print("\n=== Ray Watcher Status ===")
            print("  Status: Running ✓")
            
            # Get watcher logs (last 20 lines)
            log_result = run_command("docker logs --tail 20 ray-watcher", check=False)
            if log_result:
                print("\nRecent logs:")
                print(log_result.stdout)
        else:
            print("\n=== Ray Watcher Status ===")
            print("  Status: Not running ✗")
        print()


if __name__ == "__main__":
    main()
