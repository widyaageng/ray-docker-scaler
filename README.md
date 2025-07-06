# Ray Cluster Project

TLDR on what this do
https://www.youtube.com/watch?v=zbCSxyEH_eE


## Overview

This project implements a distributed system using Ray Serve to deploy and manage multiple microservices in a containerized environment:
Mocked Svcs:
- **Algorunner**: Executes trading algorithms and strategies
- **Screener**: Filters and screens financial data based on various criteria  
- **Tickscrawler**: Crawls and collects market tick data from various sources

## Architecture

```
raycluster/
│
├── serve_app/                    # Main Ray Serve application
│   ├── serve_app.py              # Entry point for service deployment
│   ├── router_deployment.py     # Central FastAPI router as Ray Serve deployment
│   └── config.py                 # Configuration for services
│
├── services/                     # Microservices implementations
│   ├── algorunner/               # Trading algorithm execution service
│   │   ├── deployment.py         # Ray Serve deployment
│   │   ├── logic.py              # Business logic
│   │   └── config.py             # Service configuration
│   ├── screener/                 # Financial data screening service
│   ├── tickscrawler/             # Market data crawling service
│   └── shared/                   # Shared utilities and models
│
├── scripts/                      # Cluster management scripts
│   ├── start_cluster.py          # Main cluster lifecycle management
│   ├── cluster_manager.py        # Comprehensive system management
│   ├── infra.py                  # Docker infrastructure management
│   └── autoscaler.py             # Custom autoscaler
│
├── postgres/                     # PostgreSQL configuration
├── redis/                        # Redis configuration
└── tests/                        # Test suite
```

## Features

### ✅ Current Implementation Status

- **Ray Cluster**: Running with 1 head node + 2 worker nodes in Docker containers
- **Ray Serve Deployments**: All services deployed as Ray Serve applications
- **External Access**: Ray head node binds to 0.0.0.0 for external connectivity
- **Management Scripts**: Complete cluster lifecycle and health monitoring
- **Container-based Deployment**: Services deployed inside containers for reliability
- **Centralized Routing**: Single HTTP endpoint with service-specific routes

### Service Deployment Pattern

**Individual Services (Internal with Autoscaling):**
- AlgorunnerDeployment: `algorunner` (no HTTP route, 1-10 replicas)
- ScreenerDeployment: `screener` (no HTTP route, 1-10 replicas)  
- TickscrawlerDeployment: `tickscrawler` (no HTTP route, 1-10 replicas)

**Central Router (External with Autoscaling):**
- MainRouterDeployment: `main-router` (HTTP route `/`, 1-10 replicas)
- Routes requests to individual services via Ray object references
- Provides unified API at http://localhost:8000
- Auto-scales based on request load

### Algorunner Service
- Execute trading algorithms (momentum, mean reversion, arbitrage)
- Monitor algorithm performance and execution
- Stop/start algorithm instances
- Algorithm execution history and metrics
- **Resource Allocation**: 0.2 CPU, 64MB memory
- **Scaling**: 1-10 replicas (autoscaling enabled)
- **Max Requests**: 100 concurrent requests
- **Configuration**: Via `ALGORUNNER_*` environment variables

### Screener Service  
- Filter stocks by price, volume, market cap, P/E ratio, dividend yield
- Create custom screening filters
- Market overview and sector analysis
- Real-time data screening
- **Resource Allocation**: 0.2 CPU, 64MB memory
- **Scaling**: 1-10 replicas (autoscaling enabled)
- **Max Requests**: 100 concurrent requests
- **Configuration**: Via `SCREENER_*` environment variables

### Tickscrawler Service
- Crawl data from multiple sources (Binance, Yahoo Finance, Alpha Vantage)
- Real-time streaming data connections
- Historical data retrieval
- Support for multiple data formats (ticks, OHLC, trades)
- **Resource Allocation**: 0.2 CPU, 64MB memory
- **Scaling**: 1-10 replicas (autoscaling enabled)
- **Max Requests**: 100 concurrent requests
- **Configuration**: Via `TICKSCRAWLER_*` environment variables

## Quick Start

### Prerequisites

- Python 3.9+
- Ray 2.47.1+
- FastAPI (for services)
- Requests (for watcher Dashboard API calls)
- Docker and Docker Compose
- 8GB+ RAM recommended

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd raycluster
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

### Running the System

#### Option 1: Complete System Startup (Recommended)
```bash
# Start Ray cluster with all services deployed
python scripts/start_cluster.py start --with-services

# Or use the comprehensive cluster manager
python scripts/cluster_manager.py start
```

#### Option 2: Step-by-Step Startup
```bash
# 1. Start Ray cluster only
python scripts/start_cluster.py start

# 2. Deploy services separately
python scripts/start_cluster.py deploy
```

#### Option 3: Custom Configuration
```bash
# Start with specific number of workers and memory
python scripts/start_cluster.py start --num-workers 3 --object-store-memory 2GB --with-services
```

## Management Commands

### Cluster Operations
```bash
# Check system status
python scripts/cluster_manager.py status

# Restart entire system
python scripts/cluster_manager.py restart

# Stop services only (keep cluster running)
python scripts/cluster_manager.py shutdown

# Stop entire cluster
python scripts/cluster_manager.py stop

# Deploy services to existing cluster
python scripts/cluster_manager.py deploy
```

### Advanced Cluster Management
```bash
# Get cluster information
python scripts/start_cluster.py info

# Test cluster connectivity  
python scripts/start_cluster.py connect

# Check cluster status
python scripts/start_cluster.py status

# Keep cluster running with monitoring
python scripts/start_cluster.py start --keep-alive
```

### Infrastructure Management

#### Ray Cluster Operations
```bash
# Start Ray cluster
python scripts/infra.py start-ray

# Stop Ray cluster
python scripts/infra.py stop-ray

# Check Ray cluster status
python scripts/infra.py status-ray

# View Ray logs
python scripts/infra.py logs-ray --follow

# Add additional Ray worker
python scripts/infra.py add-worker

# Start autoscaling watcher
python scripts/infra.py start-watcher

# Stop autoscaling watcher
python scripts/infra.py stop-watcher

# Check watcher status
python scripts/infra.py watcher-status
```

#### Ray Autoscaling Watcher
The Ray watcher monitors cluster load and automatically provisions new workers when needed. It uses Ray's Python API for monitoring and calls `infra.py add-worker` to scale up:

```bash
# Start watcher with custom settings
python scripts/infra.py start-watcher \
    --check-interval 10 \
    --pending-threshold 0 \
    --max-workers 5 \
    --cooldown 60
```

**Watcher Configuration:**
- `--check-interval`: How often to check cluster status (default: 10 seconds)
- `--pending-threshold`: Number of pending tasks to trigger scaling (default: 0)
- `--max-workers`: Maximum number of workers to scale to (default: 5)
- `--cooldown`: Time between scale-up events (default: 60 seconds)

**Implementation Details:**
- Uses Ray Python API (`ray.cluster_resources()`, `ray.available_resources()`) for monitoring
- Fetches accurate pending task metrics from Ray Dashboard API (`http://localhost:8265/api/cluster_status`)
- Falls back to CPU utilization heuristics if Dashboard API is unavailable
- Calls `infra.py add-worker` subprocess to provision new Docker containers
- Runs in separate container with Docker socket access for worker provisioning
- Configurable worker resources via environment variables (CPU, GPU, memory)

#### Database & Cache Services
```bash
# Start PostgreSQL and Redis
python scripts/infra.py start-infra

# Check service status
python scripts/infra.py status-infra

# View service logs
python scripts/infra.py logs-infra --service postgres --follow
```

## API Access

Once deployed, the services are available at:

- **Main API**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **Ray Dashboard**: http://localhost:8265
- **Service Endpoints**:
  - Algorunner: http://localhost:8000/api/algorunner/
  - Screener: http://localhost:8000/api/screener/
  - Tickscrawler: http://localhost:8000/api/tickscrawler/

### Complete API Reference

#### Health and Status
```bash
# Overall system health
curl http://localhost:8000/health

# Individual service status
curl http://localhost:8000/api/algorunner/status
curl http://localhost:8000/api/screener/status
curl http://localhost:8000/api/tickscrawler/status
```

#### Algorunner Service
```bash
# Run an algorithm
curl -X POST "http://localhost:8000/api/algorunner/run" \
  -H "Content-Type: application/json" \
  -d '{
    "algorithm_id": "momentum_strategy",
    "parameters": {"symbol": "AAPL", "period": 14}
  }'

# List available algorithms
curl http://localhost:8000/api/algorunner/algorithms

# Stop algorithm execution
curl -X POST "http://localhost:8000/api/algorunner/stop" \
  -H "Content-Type: application/json" \
  -d '{"algorithm_id": "momentum_strategy"}'
```

#### Screener Service
```bash
# Screen stocks with filters
curl -X POST "http://localhost:8000/api/screener/screen" \
  -H "Content-Type: application/json" \
  -d '{
    "filters": [
      {
        "type": "price_filter",
        "parameters": {"min_price": 100, "max_price": 500}
      }
    ],
    "limit": 10
  }'

# Get available filters
curl http://localhost:8000/api/screener/filters

# Get market overview
curl http://localhost:8000/api/screener/market-overview

# Create custom filter
curl -X POST "http://localhost:8000/api/screener/custom-filter" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "tech_stocks",
    "criteria": [
      {"field": "sector", "operator": "eq", "value": "Technology"},
      {"field": "market_cap", "operator": "gt", "value": 1000000000}
    ]
  }'
```

#### Tickscrawler Service
```bash
# Crawl market data
curl -X POST "http://localhost:8000/api/tickscrawler/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": "binance",
    "symbols": ["BTCUSDT", "ETHUSDT"],
    "data_type": "ticks",
    "limit": 100
  }'

# Get available data sources
curl http://localhost:8000/api/tickscrawler/sources

# Get historical data
curl -X GET "http://localhost:8000/api/tickscrawler/historical" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "interval": "1h"
  }'

# Start data streaming
curl -X POST "http://localhost:8000/api/tickscrawler/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "binance",
    "symbols": ["BTCUSDT"],
    "stream_type": "trades"
  }'
```

## Configuration

### Service Resource Limits and Autoscaling
Each service is configured with conservative resource limits and autoscaling for dynamic load handling:

- **CPU**: 0.2 cores per replica (reduced from 0.5)
- **Memory**: 64MB per replica (reduced from 128MB)
- **Base Replicas**: 1 per service (starts with 1 replica)
- **Autoscaling**: 1-10 replicas based on request load
- **Max Concurrent Requests**: 100 per service (increased from 20)
- **Scale Up Delay**: 10 seconds
- **Scale Down Delay**: 60 seconds

### Environment Variables

Key configuration options:

**Ray Cluster:**
- `RAY_HEAD_NODE`: Set to `true` on head node
- `RAY_DISABLE_IMPORT_WARNING`: Set to `1` to suppress warnings

**Algorunner Service:**
- `ALGORUNNER_REPLICAS`: Initial number of replicas (default: 1)
- `ALGORUNNER_MAX_ONGOING_REQUESTS`: Max concurrent requests (default: 100)
- `ALGORUNNER_MAX_EXECUTION_TIME`: Max execution time in seconds (default: 300)
- `ALGORUNNER_MAX_CONCURRENT`: Max concurrent algorithms (default: 10)

**Screener Service:**
- `SCREENER_REPLICAS`: Initial number of replicas (default: 1)
- `SCREENER_MAX_ONGOING_REQUESTS`: Max concurrent requests (default: 100)
- `SCREENER_REFRESH_INTERVAL`: Data refresh interval in seconds (default: 60)
- `SCREENER_MAX_RESULTS`: Max results per query (default: 1000)

**Tickscrawler Service:**
- `TICKSCRAWLER_REPLICAS`: Initial number of replicas (default: 1)
- `TICKSCRAWLER_MAX_ONGOING_REQUESTS`: Max concurrent requests (default: 100)
- `TICKSCRAWLER_MAX_CRAWLS`: Max concurrent crawls (default: 10)
- `TICKSCRAWLER_TIMEOUT`: Crawl timeout in seconds (default: 300)
- `TICKSCRAWLER_MAX_STREAMS`: Max active streams (default: 20)

**Autoscaling Configuration:**
- `*_MIN_REPLICAS`: Minimum replicas (default: 1)
- `*_MAX_REPLICAS`: Maximum replicas (default: 10)
- `*_TARGET_REQUESTS`: Target requests per replica (default: 100)
- `*_SCALE_UP_DELAY`: Scale up delay in seconds (default: 10)
- `*_SCALE_DOWN_DELAY`: Scale down delay in seconds (default: 60)

**Data Source API Keys:**
- `BINANCE_API_KEY`, `BINANCE_API_SECRET`: Binance API credentials
- `ALPHA_VANTAGE_API_KEY`: Alpha Vantage API key
- `YAHOO_FINANCE_ENABLED`: Enable Yahoo Finance (default: true)
- `FOREX_API_KEY`: Forex API key

### Ray Cluster Configuration
- **Head Node**: Binds to 0.0.0.0 for external access
- **Client Port**: 10001 (for Ray client connections)
- **Dashboard Port**: 8265
- **Serve Port**: 8000
- **Network**: ray-cluster (Docker network)
- **Object Store Memory**: 1GB per node (configurable)

### Service Configuration Files
Resource limits can be adjusted in each service's `config.py` file:

- `services/algorunner/config.py`
- `services/screener/config.py`
- `services/tickscrawler/config.py`

## Connection Information

### From Host Machine
```python
# Connect to Ray cluster via Ray client
import ray
ray.init(address='ray://localhost:10001')  # Ray client port
```

### From Inside Container
```python
# Connect from inside Ray cluster containers
import ray
ray.init(address='auto')
```

### Service Deployment
Services are deployed using `docker exec` commands to run inside the Ray head container, ensuring proper connectivity and resource management.

## Shutdown and Restart Workflows

### Clean Shutdown
```bash
# Shutdown services cleanly
python serve_app/serve_app.py shutdown

# Or shutdown everything
python scripts/cluster_manager.py stop
```

### Full Restart
```bash
# Complete system restart
python scripts/cluster_manager.py restart

# Or manual restart
python scripts/cluster_manager.py stop
python scripts/cluster_manager.py start
```

## Troubleshooting

### Common Issues

1. **Ray cluster not starting**: 
   - Check Docker is running
   - Ensure ports 8000, 8265, 10000, 10001 are available
   - Check Docker container logs: `docker logs ray-head`

2. **Service deployment fails**: 
   - Verify Ray cluster is running: `python scripts/cluster_manager.py status`
   - Check service health: `curl http://localhost:8000/health`
   - Review deployment logs

3. **Services showing as unhealthy**:
   - Services may take time to start (30-60 seconds)
   - Check individual service endpoints
   - Review Ray Serve logs in dashboard

### Diagnostic Commands

```bash
# Check container status
docker ps

# Check Ray cluster status
docker exec ray-head ray status

# View container logs
docker logs ray-head
docker logs ray-worker-1

# Test service connectivity
curl -w "%{http_code}" http://localhost:8000/health
```

## Development

### Adding New Services

1. Create service directory under `services/`
2. Implement `deployment.py`, `logic.py`, and `config.py`
3. Add service routes to `serve_app/router_deployment.py`
4. Update `serve_app/serve_app.py` to deploy the new service
5. Add tests in `tests/`

### Service Development Pattern

**Create a new service with autoscaling:**
```python
# services/newservice/config.py
@dataclass
class NewServiceConfig:
    name: str = "newservice"
    max_ongoing_requests: int = 100
    min_replicas: int = 1
    max_replicas: int = 10
    target_num_ongoing_requests_per_replica: int = 100
    scale_up_delay_s: int = 10
    scale_down_delay_s: int = 60
    ray_actor_options: Dict[str, Any] = None

# services/newservice/deployment.py
@serve.deployment(
    name="newservice",
    max_ongoing_requests=NEWSERVICE_CONFIG.max_ongoing_requests,
    autoscaling_config={
        "min_replicas": NEWSERVICE_CONFIG.min_replicas,
        "max_replicas": NEWSERVICE_CONFIG.max_replicas,
        "target_ongoing_requests": NEWSERVICE_CONFIG.target_num_ongoing_requests_per_replica,
        "scale_up_delay_s": NEWSERVICE_CONFIG.scale_up_delay_s,
        "scale_down_delay_s": NEWSERVICE_CONFIG.scale_down_delay_s
    },
    ray_actor_options={"num_cpus": 0.2, "memory": 64 * 1024 * 1024}
)
class NewServiceDeployment:
    def __init__(self):
        self.logic = NewServiceLogic()
    
    async def process(self, request_data):
        return await self.logic.process_data(request_data)
```

**Add to router:**
```python
# serve_app/router_deployment.py
@app.post("/api/newservice/process")
async def process_data(self, request: Request):
    body = await request.json()
    result = await self.newservice_handle.process.remote(body)
    return result
```

**Deploy in serve_app:**
```python
# serve_app/serve_app.py
newservice_handle = serve.run(NewServiceDeployment.bind(), name="newservice", route_prefix=None)
```

### Testing

```bash
# Run all tests
pytest

# Run specific test files
pytest tests/test_algorunner.py
pytest tests/test_screener.py
pytest tests/test_integration.py

# Run with coverage
pytest --cov=services tests/

# Test specific endpoints
curl http://localhost:8000/api/algorunner/status
curl http://localhost:8000/api/screener/status
curl http://localhost:8000/api/tickscrawler/status
```

### Code Quality

```bash
# Format code
black .

# Lint code
flake8 .

# Type checking
mypy .
```

### Development Workflow

1. **Start development environment:**
```bash
python scripts/start_cluster.py start --with-services
```

2. **Make changes to services**
3. **Restart services (keep cluster running):**
```bash
python scripts/cluster_manager.py shutdown
python scripts/cluster_manager.py deploy
```

4. **Test changes:**
```bash
curl http://localhost:8000/health
pytest tests/
```

5. **Full restart if needed:**
```bash
python scripts/cluster_manager.py restart
```

## Infrastructure Components

- **Ray Cluster**: Distributed computing framework (Docker-based)
- **Ray Serve**: HTTP service deployment platform
- **Docker**: Containerization platform
- **PostgreSQL**: Persistent data storage (optional, configured)
- **Redis**: Caching and session storage (optional, configured)
- **FastAPI**: HTTP API framework (via Ray Serve)

### Service Architecture

**Ray Serve Deployment Pattern:**
- Individual services deployed without HTTP routes
- Central router handles all HTTP traffic
- Services communicate via Ray object references
- Single external endpoint for all services
- **Autoscaling**: All services scale automatically from 1-10 replicas
- **Load Balancing**: Ray Serve automatically load balances between replicas

**Container Architecture:**
- Ray head node: Contains all services and HTTP server
- Ray worker nodes: Provide additional compute capacity
- All containers share the same workspace volume
- Services deployed using `docker exec` for reliability
- **Dynamic Scaling**: Services scale up/down based on request load

## System Requirements

- **CPU**: 2+ cores recommended
- **Memory**: 4GB+ RAM (8GB+ recommended)
- **Storage**: 10GB+ free space
- **Network**: Docker networking enabled

## Production Considerations

For production deployment:

1. **Resource Scaling**: Adjust CPU/memory limits in service configs
2. **High Availability**: Deploy multiple replicas per service
3. **Monitoring**: Enable Ray metrics and logging
4. **Security**: Configure authentication and HTTPS
5. **Persistence**: Enable database services for state management
6. **Load Balancing**: Configure external load balancer for Ray Serve
7. **Container Orchestration**: Use Kubernetes or Docker Swarm

### Production Configuration Example

```python
# services/algorunner/config.py (production)
ALGORUNNER_SERVICE_CONFIG = AlgorunnerServiceConfig(
    max_ongoing_requests=200,  # Higher concurrency
    min_replicas=2,  # Start with more replicas
    max_replicas=20,  # Allow more scaling
    target_num_ongoing_requests_per_replica=50,  # Lower target for better performance
    ray_actor_options={
        "num_cpus": 1.0,  # More CPU
        "memory": 512 * 1024 * 1024  # More memory
    }
)
```

### Environment Variables for Production

```bash
# Scale services
ALGORUNNER_REPLICAS=2  # Start with more replicas
SCREENER_REPLICAS=2
TICKSCRAWLER_REPLICAS=2

# Increase limits and performance
ALGORUNNER_MAX_ONGOING_REQUESTS=200
SCREENER_MAX_ONGOING_REQUESTS=150
TICKSCRAWLER_MAX_ONGOING_REQUESTS=200

# Autoscaling configuration
ALGORUNNER_MIN_REPLICAS=2
ALGORUNNER_MAX_REPLICAS=20
ALGORUNNER_TARGET_REQUESTS=50

# API keys
BINANCE_API_KEY=your_binance_api_key
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
```

## Support

- **Ray Documentation**: https://docs.ray.io/
- **Ray Serve Guide**: https://docs.ray.io/en/latest/serve/
- **Docker Documentation**: https://docs.docker.com/

---

**Note**: This is a development/demonstration setup. For production use, implement proper security, monitoring, and resource management configurations.
