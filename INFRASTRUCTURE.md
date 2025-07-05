# Infrastructure Setup

This document describes the infrastructure components for the Ray Cluster project, including the Docker-based Ray cluster and Ray Serve deployments.

## Architecture Overview

The infrastructure consists of three main components:

1. **Ray Cluster** - Docker containers running Ray head and worker nodes
2. **Ray Serve Services** - Microservices deployed as Ray Serve applications
3. **Supporting Services** - PostgreSQL, Redis, and admin tools

## Ray Cluster Components

### Ray Head Node
- **Image**: rayproject/ray:2.47.1.aeaf41-py39-cpu
- **Container**: ray-head
- **Network**: ray-cluster
- **Ports**:
  - 10000: Ray internal communication
  - 10001: Ray client connections
  - 8265: Ray dashboard
  - 8000: Ray Serve API
- **Configuration**: `--node-ip-address=0.0.0.0` for external access
- **Volume Mounts**: 
  - `/workspace`: Project source code
  - `/tmp/ray`: Ray logs and state

### Ray Worker Nodes
- **Image**: rayproject/ray:2.47.1.aeaf41-py39-cpu
- **Containers**: ray-worker-1, ray-worker-2, ...
- **Network**: ray-cluster
- **Configuration**: Connects to head node at ray-head:10000
- **Volume Mounts**: Same as head node for shared workspace

## Ray Serve Services

### Service Deployment Architecture
All services are deployed as Ray Serve deployments with:
- **Deployment Pattern**: Individual services + centralized router
- **Communication**: Internal Ray object references
- **External Access**: Single HTTP endpoint (port 8000)
- **Service Discovery**: Via Ray Serve's internal routing

### MainRouterDeployment
- **Name**: main-router
- **Route Prefix**: `/`
- **Autoscaling**: 1-10 replicas
- **Max Ongoing Requests**: 100
- **Resources**: 0.3 CPU, 64MB memory
- **Purpose**: Central FastAPI router that routes requests to individual services
- **Load Balancing**: Automatic across replicas

### Individual Service Deployments

#### AlgorunnerDeployment
- **Name**: algorunner
- **Route Prefix**: None (internal service)
- **Autoscaling**: 1-10 replicas (configurable via environment variables)
- **Max Ongoing Requests**: 100
- **Resources**: 0.2 CPU, 64MB memory per replica
- **Scale Up Delay**: 10 seconds
- **Scale Down Delay**: 60 seconds
- **Purpose**: Execute trading algorithms and strategies
- **Endpoints**:
  - `POST /api/algorunner/run`: Execute algorithm
  - `GET /api/algorunner/status`: Get service status
  - `GET /api/algorunner/algorithms`: List algorithms
  - `POST /api/algorunner/stop`: Stop algorithm execution

#### ScreenerDeployment
- **Name**: screener
- **Route Prefix**: None (internal service)
- **Autoscaling**: 1-10 replicas (configurable via environment variables)
- **Max Ongoing Requests**: 100
- **Resources**: 0.2 CPU, 64MB memory per replica
- **Scale Up Delay**: 10 seconds
- **Scale Down Delay**: 60 seconds
- **Purpose**: Filter and screen financial data
- **Endpoints**:
  - `POST /api/screener/screen`: Screen data with filters
  - `GET /api/screener/filters`: Get available filters
  - `GET /api/screener/status`: Get service status
  - `POST /api/screener/custom-filter`: Create custom filter
  - `GET /api/screener/market-overview`: Get market overview

#### TickscrawlerDeployment
- **Name**: tickscrawler
- **Route Prefix**: None (internal service)
- **Autoscaling**: 1-10 replicas (configurable via environment variables)
- **Max Ongoing Requests**: 100
- **Resources**: 0.2 CPU, 64MB memory per replica
- **Scale Up Delay**: 10 seconds
- **Scale Down Delay**: 60 seconds
- **Purpose**: Crawl and collect market tick data
- **Endpoints**:
  - `POST /api/tickscrawler/crawl`: Crawl tick data
  - `GET /api/tickscrawler/sources`: Get available data sources
  - `GET /api/tickscrawler/status`: Get service status
  - `POST /api/tickscrawler/stream`: Start streaming data
  - `DELETE /api/tickscrawler/stream/{id}`: Stop streaming
  - `GET /api/tickscrawler/historical`: Get historical data

## Supporting Services

### PostgreSQL Database
- **Image**: postgres:15-alpine
- **Container**: ray-postgres
- **Port**: 5432
- **Database**: raycluster
- **Username**: rayuser
- **Password**: raypassword

### Redis Cache
- **Image**: redis:7-alpine
- **Container**: ray-redis
- **Port**: 6379
- **Password**: redispassword
- **Note**: Ray has its own internal Redis, external Redis is optional

### Admin Tools

#### pgAdmin (PostgreSQL Admin)
- **Image**: dpage/pgadmin4
- **Container**: ray-pgadmin
- **Port**: 8080
- **URL**: http://localhost:8080
- **Email**: admin@raycluster.com
- **Password**: admin

## Usage

### Complete System Management

#### Using the Cluster Manager (Recommended)
```bash
# Start complete system (Ray cluster + services)
python scripts/cluster_manager.py start

# Check system status
python scripts/cluster_manager.py status

# Restart entire system
python scripts/cluster_manager.py restart

# Stop services only (keep cluster running)
python scripts/cluster_manager.py shutdown

# Stop entire system
python scripts/cluster_manager.py stop

# Deploy services to existing cluster
python scripts/cluster_manager.py deploy
```

#### Using Start Cluster Script
```bash
# Start Ray cluster with services
python scripts/start_cluster.py start --with-services

# Start Ray cluster only
python scripts/start_cluster.py start

# Deploy services to existing cluster
python scripts/start_cluster.py deploy

# Stop Ray cluster
python scripts/start_cluster.py stop

# Check cluster status
python scripts/start_cluster.py status
```

### Ray Cluster Management

#### Start Ray Cluster
```bash
# Start complete Ray cluster (head + 2 workers)
python scripts/infra.py start-ray

# Start with custom configuration
python scripts/infra.py start-ray --num-workers 3 --object-store-memory 2GB --num-cpus 2
```

#### Stop Ray Cluster
```bash
python scripts/infra.py stop-ray
```

#### Restart Ray Cluster
```bash
python scripts/infra.py restart-ray
```

#### Check Ray Cluster Status
```bash
python scripts/infra.py status-ray
```

#### View Ray Cluster Logs
```bash
# All containers
python scripts/infra.py logs-ray

# Specific container
python scripts/infra.py logs-ray --service head
python scripts/infra.py logs-ray --service worker-1

# Follow logs
python scripts/infra.py logs-ray --service head --follow
```

#### Ray Cluster Autoscaling

The Ray watcher service monitors cluster load and automatically provisions new workers when needed:

```bash
# Start Ray watcher with default settings
python scripts/infra.py start-watcher

# Start with custom configuration
python scripts/infra.py start-watcher \
    --check-interval 120 \
    --pending-threshold 5 \
    --max-workers 10 \
    --cooldown 300

# Stop watcher
python scripts/infra.py stop-watcher

# Check watcher status
python scripts/infra.py watcher-status

# Manually add a worker
python scripts/infra.py add-worker
```

**Watcher Configuration:**
- `--check-interval`: How often to check cluster status (default: 120 seconds)
- `--pending-threshold`: Number of pending tasks to trigger scaling (default: 5)
- `--max-workers`: Maximum number of workers to scale to (default: 10)
- `--cooldown`: Time between scale-up events (default: 300 seconds)

**Watcher Behavior:**
- Monitors Ray cluster every 2 minutes by default
- Scales up when pending tasks exceed threshold
- Ensures worker indices are continuous (ray-worker-1, ray-worker-2, etc.)
- Respects cooldown period to prevent rapid scaling
- Automatically stops scaling at max worker limit
- Runs in a separate Docker container with access to Docker daemon

### Ray Serve Services Management

#### Service Deployment
Services are deployed inside the Ray head container using `docker exec`:

```bash
# Deploy all services
docker exec ray-head python /workspace/serve_app/serve_app.py

# Or use the deployment script
docker exec ray-head python /workspace/deploy_inside_cluster.py
```

#### Service Configuration
Each service can be configured via environment variables:

**Algorunner Service:**
```bash
ALGORUNNER_REPLICAS=1                    # Initial number of replicas
ALGORUNNER_MAX_ONGOING_REQUESTS=100      # Max concurrent requests
ALGORUNNER_MAX_EXECUTION_TIME=300        # Max execution time (seconds)
ALGORUNNER_MAX_CONCURRENT=10             # Max concurrent algorithms

# Autoscaling configuration
ALGORUNNER_MIN_REPLICAS=1                # Minimum replicas
ALGORUNNER_MAX_REPLICAS=10               # Maximum replicas
ALGORUNNER_TARGET_REQUESTS=100           # Target requests per replica
ALGORUNNER_SCALE_UP_DELAY=10             # Scale up delay (seconds)
ALGORUNNER_SCALE_DOWN_DELAY=60           # Scale down delay (seconds)
```

**Screener Service:**
```bash
SCREENER_REPLICAS=1                      # Initial number of replicas
SCREENER_MAX_ONGOING_REQUESTS=100        # Max concurrent requests
SCREENER_REFRESH_INTERVAL=60             # Data refresh interval (seconds)
SCREENER_MAX_RESULTS=1000                # Max results per query

# Autoscaling configuration
SCREENER_MIN_REPLICAS=1                  # Minimum replicas
SCREENER_MAX_REPLICAS=10                 # Maximum replicas
SCREENER_TARGET_REQUESTS=100             # Target requests per replica
SCREENER_SCALE_UP_DELAY=10               # Scale up delay (seconds)
SCREENER_SCALE_DOWN_DELAY=60             # Scale down delay (seconds)
```

**Tickscrawler Service:**
```bash
TICKSCRAWLER_REPLICAS=1                  # Initial number of replicas
TICKSCRAWLER_MAX_ONGOING_REQUESTS=100    # Max concurrent requests
TICKSCRAWLER_MAX_CRAWLS=10               # Max concurrent crawls
TICKSCRAWLER_TIMEOUT=300                 # Crawl timeout (seconds)
TICKSCRAWLER_MAX_STREAMS=20              # Max active streams

# Autoscaling configuration
TICKSCRAWLER_MIN_REPLICAS=1              # Minimum replicas
TICKSCRAWLER_MAX_REPLICAS=10             # Maximum replicas
TICKSCRAWLER_TARGET_REQUESTS=100         # Target requests per replica
TICKSCRAWLER_SCALE_UP_DELAY=10           # Scale up delay (seconds)
TICKSCRAWLER_SCALE_DOWN_DELAY=60         # Scale down delay (seconds)
```

#### Service Health Checks
```bash
# Check all services
curl http://localhost:8000/health

# Check individual service status
curl http://localhost:8000/api/algorunner/status
curl http://localhost:8000/api/screener/status
curl http://localhost:8000/api/tickscrawler/status
```

### Supporting Services Management

#### Start Infrastructure Services
```bash
python scripts/infra.py start-infra
```

#### Stop Infrastructure Services
```bash
python scripts/infra.py stop-infra
```

#### Restart Infrastructure Services
```bash
python scripts/infra.py restart-infra
```

#### Check Infrastructure Status
```bash
python scripts/infra.py status-infra
```

#### View Infrastructure Logs
```bash
# All services
python scripts/infra.py logs-infra

# Specific service
python scripts/infra.py logs-infra --service postgres

# Follow logs
python scripts/infra.py logs-infra --service postgres --follow
```

#### Connection Information
```bash
python scripts/infra.py info-infra
```

#### Clean Up Infrastructure (Remove all data)
```bash
python scripts/infra.py cleanup-infra
```

## Complete System Management

For integrated management of both Ray cluster and supporting services, use the higher-level scripts:

```bash
# Start complete system (infrastructure + Ray cluster + services)
python scripts/start_cluster.py start --with-services

# Or use the comprehensive cluster manager
python scripts/cluster_manager.py start
```

## Network Configuration

### Ray Cluster Network
- **Network Name**: ray-cluster
- **Type**: Docker bridge network
- **Subnet**: Automatically assigned by Docker
- **Internal Communication**: All Ray containers communicate via container names
- **External Access**: Head node binds to 0.0.0.0 for external connectivity

### Port Mappings
- **Ray Head Node**:
  - 10000 → 10000: Ray internal communication
  - 10001 → 10001: Ray client connections  
  - 8265 → 8265: Ray dashboard
  - 8000 → 8000: Ray Serve API
- **Infrastructure Services**:
  - 5432 → 5432: PostgreSQL
  - 6379 → 6379: Redis
  - 8080 → 8080: pgAdmin

## Ray Cluster Configuration

### Resource Limits and Autoscaling
- **Default CPUs per replica**: 0.2 (algorunner, screener, tickscrawler), 0.3 (router)
- **Default Memory per replica**: 64MB
- **Default Object Store Memory**: 1GB per Ray node
- **Autoscaling Range**: 1-10 replicas per service
- **Scale Up Delay**: 10 seconds (configurable)
- **Scale Down Delay**: 60 seconds (configurable)
- **Target Load**: 100 requests per replica (configurable)
- **Configurable via CLI**: `--num-cpus`, `--object-store-memory`

### Container Configuration
- **Init Process**: Enabled (`--init`) for proper signal handling
- **Workspace Mount**: Project directory mounted at `/workspace`
- **Log Directory**: `./logs` mounted at `/tmp/ray`
- **Working Directory**: `/workspace` in all containers

### Environment Variables
- **RAY_HEAD_NODE=true**: Set on head node
- **RAY_HEAD_ADDRESS=ray-head:10000**: Set on worker nodes
- **RAY_DISABLE_IMPORT_WARNING=1**: Suppress import warnings

### Autoscaling Behavior
- **Scale Up**: When average requests per replica > target for scale_up_delay seconds
- **Scale Down**: When average requests per replica < target for scale_down_delay seconds
- **Load Balancing**: Ray Serve automatically distributes requests across replicas
- **Health Monitoring**: Unhealthy replicas are automatically replaced

## Database Schema

The PostgreSQL database is automatically initialized with:

- **Schemas**: algorunner, screener, tickscrawler, shared
- **Extensions**: uuid-ossp, pg_stat_statements, pg_trgm, btree_gin, btree_gist
- **Tables**: Pre-created tables for all services with proper indexes
- **Sample Data**: Initial algorithms and data sources

## Configuration Files

### Environment Variables
Infrastructure services use the `.env` file:

```env
# PostgreSQL
POSTGRES_DB=raycluster
POSTGRES_USER=rayuser
POSTGRES_PASSWORD=raypassword
POSTGRES_PORT=5432

# Redis
REDIS_PASSWORD=redispassword
REDIS_PORT=6379

# Admin Tools
PGADMIN_EMAIL=admin@raycluster.com
PGADMIN_PASSWORD=admin
PGADMIN_PORT=8080
```

### Volume Mounts
- **PostgreSQL Data**: `./postgres/data`
- **PostgreSQL Config**: `./postgres/config`
- **PostgreSQL Init Scripts**: `./postgres/init`
- **Redis Data**: `./redis/data`
- **Redis Config**: `./redis/config`
- **Ray Logs**: `./logs`

## Health Checks and Monitoring

### Ray Cluster Health
- **Head Node**: `ray status` command execution
- **Worker Nodes**: Connection status via Ray dashboard
- **Service Endpoints**: HTTP health checks on service ports

### Infrastructure Health
- **PostgreSQL**: `pg_isready` check
- **Redis**: `redis-cli ping` check
- **Health Check Interval**: Every 10 seconds

## Performance Tuning

### Ray Cluster
- **Object Store Memory**: Configurable per node (default 1GB)
- **CPU Allocation**: Configurable per node (default 1)
- **Shared Memory**: 2GB per container for efficient data sharing

### PostgreSQL
- **Shared Buffers**: 256MB
- **Effective Cache Size**: 1GB
- **Max Connections**: 200
- **Work Memory**: 4MB
- **Maintenance Work Memory**: 64MB

### Redis
- **Max Memory**: 512MB
- **Max Memory Policy**: allkeys-lru
- **Persistence**: AOF + RDB snapshots
- **Append Sync**: everysec

## Security Notes

⚠️ **Important**: The default passwords are for development only. Change them for production use:

1. Update passwords in `.env` file
2. Restart infrastructure: `python scripts/infra.py restart-infra`
3. Consider using Docker secrets for production deployments

## Troubleshooting

### Common Issues

#### Ray Cluster Issues
1. **Head node not starting**: Check Docker logs with `python scripts/infra.py logs-ray --service head`
2. **Workers not connecting**: Verify network connectivity and head node status
3. **Port conflicts**: Ensure ports 10000, 10001, 8265, 8000 are available
4. **Memory issues**: Increase object store memory with `--object-store-memory`

#### Infrastructure Issues
1. **Database connection issues**: Check PostgreSQL logs and network connectivity
2. **Redis connection failures**: Verify Redis container status and password
3. **Permission issues**: Ensure Docker has proper permissions for volume mounts

### Debugging Commands

#### Ray Cluster Debugging
```bash
# Check Ray cluster status
python scripts/infra.py status-ray

# View Ray head logs
python scripts/infra.py logs-ray --service head --follow

# Check Ray dashboard
curl http://localhost:8265

# Test Ray client connection
python -c "import ray; ray.init('ray://localhost:10001'); print(ray.cluster_resources())"
```

#### Infrastructure Debugging
```bash
# Check all container status
docker ps --filter network=ray-cluster

# Test database connection
docker exec -it ray-postgres psql -U rayuser -d raycluster -c "SELECT version();"

# Test Redis connection
docker exec -it ray-redis redis-cli -a redispassword ping

# Check network connectivity
docker network inspect ray-cluster
```

### Log Locations
- **Ray Logs**: `./logs/` (mounted from containers)
- **Container Logs**: `docker logs <container-name>`
- **Infrastructure Logs**: `docker compose logs`

## Development Notes

### Making Changes
1. **Code Changes**: Mount point `/workspace` reflects live changes
2. **Service Restart**: Use `python scripts/cluster_manager.py restart` to reload services
3. **Cluster Rebuild**: Use `python scripts/infra.py restart-ray` to rebuild Ray cluster

### Testing
1. **Unit Tests**: Run inside Ray containers with shared workspace
2. **Integration Tests**: Test full system with `python scripts/start_cluster.py start --with-services`
3. **Service Tests**: Individual service testing via Ray Serve endpoints
