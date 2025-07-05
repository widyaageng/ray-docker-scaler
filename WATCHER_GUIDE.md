# Ray Cluster Watcher Usage Guide

This guide demonstrates how to use the Ray watcher service for automatic scaling.

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
