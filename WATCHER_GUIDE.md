# Ray Cluster Watcher Usage Guide

This guide demonstrates how to use the Ray watcher service for automatic scaling and provides a comprehensive overview of the watcher implementation.

## Quick Start

### 1. Start Ray Cluster
```bash
# Start Ray cluster with 2 workers
python scripts/infra.py start-ray --num-workers 2

# Check cluster status
python scripts/infra.py status-ray
```

### 2. Start Ray Watcher
```bash
# Start watcher with default settings
python scripts/infra.py start-watcher

# Or start with custom configuration
python scripts/infra.py start-watcher \
    --check-interval 60 \
    --pending-threshold 3 \
    --max-workers 8 \
    --cooldown 120
```

### 3. Test Autoscaling
```bash
# Run the test script to generate pending tasks
python test_watcher.py

# Monitor watcher activity
python scripts/infra.py watcher-status
```

### 4. Manual Operations
```bash
# Add a worker manually
python scripts/infra.py add-worker

# Stop the watcher
python scripts/infra.py stop-watcher

# Stop the entire cluster
python scripts/infra.py stop-ray
```

## Configuration Options

### Watcher Parameters
- `--check-interval`: How often to check cluster status (seconds)
- `--pending-threshold`: Number of pending tasks to trigger scaling
- `--max-workers`: Maximum number of workers to scale to
- `--cooldown`: Time between scale-up events (seconds)

### Ray Cluster Parameters
- `--num-workers`: Initial number of worker nodes
- `--num-cpus`: Number of CPUs per Ray node
- `--num-gpus`: Number of GPUs per Ray node
- `--object-store-memory`: Object store memory limit per Ray node

## Monitoring and Troubleshooting

### Check Cluster Status
```bash
# Overall cluster status
python scripts/infra.py status-ray

# Watcher status and logs
python scripts/infra.py watcher-status

# Ray dashboard
open http://localhost:8265
```

### View Logs
```bash
# Ray head node logs
python scripts/infra.py logs-ray --service head

# Worker logs
python scripts/infra.py logs-ray --service worker-1

# Watcher logs
docker logs ray-watcher
```

### Common Issues

1. **Watcher not scaling**: Check if pending tasks exceed threshold
2. **Worker connection issues**: Ensure Ray cluster network is healthy
3. **Docker permission issues**: Ensure Docker daemon is accessible
4. **Resource limits**: Check if system has enough resources for new workers

## Advanced Usage

### Integration with Ray Serve
The watcher works seamlessly with Ray Serve autoscaling:

```python
import ray
from ray import serve

# Connect to cluster
ray.init(address="ray://localhost:10001")

# Start Serve
serve.start()

# Deploy service with autoscaling
@serve.deployment(
    num_replicas=2,
    max_concurrent_queries=100,
    autoscaling_config={
        "min_replicas": 1,
        "max_replicas": 10,
        "target_num_ongoing_requests_per_replica": 5,
    }
)
class MyService:
    def __call__(self, request):
        # Your service logic here
        return {"result": "processed"}

MyService.deploy()
```

### Custom Scaling Logic
The watcher can be extended with custom scaling logic by modifying the `scale_up_worker()` function in the watcher script.

## Best Practices

1. **Start small**: Begin with default settings and adjust based on workload
2. **Monitor resources**: Ensure sufficient CPU/memory for new workers
3. **Set appropriate thresholds**: Balance responsiveness with resource usage
4. **Use cooldown periods**: Prevent rapid scaling oscillations
5. **Test thoroughly**: Verify autoscaling behavior with your workload
6. **Monitor logs**: Keep an eye on watcher and worker logs
7. **Plan for failures**: Have fallback strategies for scaling issues

## Architecture and Implementation

### Watcher Architecture

The Ray watcher implementation follows a hybrid architecture combining Ray's Python API with Docker container management:

**File: `scripts/ray_watcher.py`**
- Standalone Python script for the Ray watcher service
- Uses Ray's Python API (`ray.cluster_resources()`, `ray.available_resources()`) for cluster monitoring
- Fetches accurate pending task metrics from Ray Dashboard API endpoints
- Falls back to CPU utilization heuristics if Dashboard API is unavailable
- Calls `infra.py add-worker` subprocess to provision new Docker worker containers
- Configured to read settings from environment variables including worker resource specs
- Includes proper error handling and logging with HTTP request timeout handling

**File: `scripts/infra.py`**
- Modified `start_ray_watcher()` function to use the separate watcher script
- Updated container mount to use `/workspace/scripts/ray_watcher.py` directly
- Restored Docker socket mount for worker container provisioning
- Passes Ray head address and configuration via environment variables

### Key Improvements

**Cleaner Architecture:**
- Watcher logic is now in a separate, maintainable file
- Uses Ray's Python API + Ray Dashboard API for accurate cluster monitoring
- Falls back to CPU-based heuristics when Dashboard API is unavailable
- Environment variables are used for configuration
- Hybrid approach: Ray API for monitoring + subprocess calls for scaling

**Better Container Setup:**
- Uses workspace mount (`/workspace`) for script access
- Connects to Ray cluster via Ray client API for monitoring
- Accesses Ray Dashboard API for accurate pending task metrics
- Docker socket mounted for worker container provisioning
- Proper environment variable passing for Ray connection and worker specs

**Configuration:**
- `WATCHER_CHECK_INTERVAL`: Check frequency (default: 10 seconds)
- `WATCHER_PENDING_THRESHOLD`: Tasks threshold (default: 0)
- `WATCHER_MAX_WORKERS`: Maximum workers (default: 5)
- `WATCHER_COOLDOWN`: Scale-up cooldown (default: 60 seconds)
- `RAY_HEAD_ADDRESS`: Ray head node address (default: localhost:10001)
- `RAY_DASHBOARD_METRIC_API`: Dashboard API base URL (default: http://localhost:8265/api)
- `WATCHER_NUM_CPUS`: CPUs per new worker (default: 1)
- `WATCHER_NUM_GPUS`: GPUs per new worker (default: 0)
- `WATCHER_OBJECT_STORE_MEMORY`: Object store memory per worker (default: 1GB)

### Container Command

The watcher now runs with this command:
```bash
docker run -d \
    --name ray-watcher \
    --network ray-cluster \
    --init \
    -v $(pwd):/workspace \
    -v $(pwd)/logs:/tmp/ray \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -w /workspace \
    -e WATCHER_CHECK_INTERVAL=10 \
    -e WATCHER_PENDING_THRESHOLD=0 \
    -e WATCHER_MAX_WORKERS=5 \
    -e WATCHER_COOLDOWN=60 \
    -e RAY_HEAD_ADDRESS=localhost:10001 \
    -e RAY_DISABLE_IMPORT_WARNING=1 \
    rayproject/ray:2.47.1.aeaf41-py39-cpu \
    bash -c 'apt-get update && apt-get install -y docker.io && python /workspace/scripts/ray_watcher.py'
```

### Benefits

1. **Maintainability**: Watcher logic is in a separate file for easier editing
2. **Accurate Monitoring**: Uses Ray Dashboard API for precise pending task detection
3. **Fallback Resilience**: CPU-based heuristics when Dashboard API is unavailable
4. **Configuration**: Clean environment variable-based configuration
5. **Deployment**: Simplified container setup using workspace mount
6. **Scalability**: Actual worker provisioning via proven Docker container management
7. **Resource Control**: Configurable CPU, GPU, and memory specifications for new workers

## Testing

### Test Files

**Updated Test Files:**
- `tests/test_watcher.py`: Integration tests for the watcher service
- `tests/test_watcher_logic.py`: Unit tests for watcher logic functions
- `tests/test_watcher_suite.py`: Comprehensive test runner

**Test Coverage:**
- Watcher script existence and syntax validation
- Individual function testing (worker indexing, metrics parsing)
- Environment variable configuration testing
- Command-line interface validation
- Integration testing with live Ray cluster (when available)
- Container management testing

**Running Tests:**
```bash
# Run individual tests
python tests/test_watcher_logic.py
python tests/test_watcher.py

# Run comprehensive test suite
python tests/test_watcher_suite.py
```

### Test Categories

1. **Unit Tests**: Test individual functions and logic
2. **Integration Tests**: Test interaction with Ray cluster
3. **Configuration Tests**: Test environment variable handling
4. **Syntax Tests**: Validate Python syntax of watcher script
5. **CLI Tests**: Test command-line interface functionality
