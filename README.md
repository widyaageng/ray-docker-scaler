# Ray Cluster Project

A scalable Ray-based microservices architecture for financial data processing, algorithmic trading, and market analysis.

## Overview

This project implements a distributed system using Ray Serve to deploy and manage multiple microservices:

- **Algorunner**: Executes trading algorithms and strategies
- **Screener**: Filters and screens financial data based on various criteria  
- **Tickscrawler**: Crawls and collects market tick data from various sources

## Architecture

```
ray_cluster_project/
│
├── serve_app/                    # Main Ray Serve app entry
│   ├── __init__.py
│   ├── serve_app.py              # Entry point to Ray Serve deployments
│   ├── config.py                 # Config for services / routers
│   └── router.py                 # Central router (FastAPI)
│
├── services/                     # All microservices/deployments
│   ├── algorunner/               # Trading algorithm execution service
│   ├── screener/                 # Financial data screening service
│   ├── tickscrawler/             # Market data crawling service
│   └── shared/                   # Shared utilities and models
│
├── scripts/                      # Cluster management scripts
│   ├── deploy.py                 # Deployment script
│   ├── start_cluster.py         # Cluster startup script
│   └── autoscaler.py            # Custom autoscaler
│
└── tests/                        # Test suite
```

## Features

### Algorunner Service
- Execute trading algorithms (momentum, mean reversion, arbitrage)
- Monitor algorithm performance and execution
- Stop/start algorithm instances
- Algorithm execution history and metrics

### Screener Service  
- Filter stocks by price, volume, market cap, P/E ratio, dividend yield
- Create custom screening filters
- Market overview and sector analysis
- Real-time data screening

### Tickscrawler Service
- Crawl data from multiple sources (Binance, Yahoo Finance, Alpha Vantage)
- Real-time streaming data connections
- Historical data retrieval
- Support for multiple data formats (ticks, OHLC, trades)

## Quick Start

### Prerequisites

- Python 3.8+
- Ray 2.9.0+
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

3. Start infrastructure services:
```bash
python scripts/infra.py start
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

### Running the Services

#### Option 1: Quick Start (Containerized Cluster)
```bash
# Start Ray cluster in Docker containers
python scripts/start_cluster.py start

# Deploy services to the cluster
python scripts/deploy.py deploy

# Check cluster status
python scripts/start_cluster.py status
```

#### Option 2: Multi-Worker Setup
```bash
# Start Ray cluster with multiple workers
python scripts/start_cluster.py start --num-workers 3 --num-cpus 4 --object-store-memory 2GB

# Deploy services
python scripts/deploy.py deploy

# Monitor cluster
python scripts/start_cluster.py status
```

### Infrastructure Management

#### Ray Cluster Operations
```bash
# Start Ray cluster
python scripts/infra.py start-ray

# Stop Ray cluster
python scripts/infra.py stop-ray

# Check Ray cluster status
python scripts/infra.py ray-status

# View Ray logs
python scripts/infra.py ray-logs --follow
```

#### Database & Cache Services
```bash
# Start PostgreSQL and Redis
python scripts/infra.py start

# Check service status
python scripts/infra.py status

# View service logs
python scripts/infra.py logs --service postgres --follow
```

### API Usage

Once deployed, the services are available at:

- **Main API**: http://localhost:8000
- **Health Check**: http://localhost:8000/health
- **Ray Dashboard**: http://localhost:8265

#### Example API Calls

**Run an Algorithm:**
```bash
curl -X POST "http://localhost:8000/api/algorunner/run" \
  -H "Content-Type: application/json" \
  -d '{
    "algorithm_id": "momentum_strategy",
    "parameters": {"symbol": "AAPL", "period": 14}
  }'
```

**Screen Stocks:**
```bash
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
```

**Crawl Market Data:**
```bash
curl -X POST "http://localhost:8000/api/tickscrawler/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": "binance",
    "symbols": ["BTCUSDT", "ETHUSDT"],
    "data_type": "ticks",
    "limit": 100
  }'
```

## Configuration

### Environment Variables

Key configuration options in `.env`:

- `SERVE_HOST`, `SERVE_PORT`: Ray Serve host and port
- `*_REPLICAS`: Number of replicas for each service
- `*_MAX_QUERIES`: Concurrent query limits
- API keys for data sources (Binance, Alpha Vantage, etc.)

### Service Configuration

Each service has its own configuration in `services/*/config.py`:

- Resource allocation (CPU, memory)
- Service-specific parameters
- Data source settings

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test files
pytest tests/test_algorunner.py
pytest tests/test_screener.py
pytest tests/test_integration.py

# Run with coverage
pytest --cov=services tests/
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

### Adding New Services

1. Create service directory under `services/`
2. Implement `deployment.py`, `logic.py`, and `config.py`
3. Add service routes to `serve_app/router.py`
4. Update `serve_app/serve_app.py` to deploy the new service
5. Add tests in `tests/`

## Deployment

### Local Development
```bash
python scripts/start_cluster.py single --num-cpus 4
python scripts/deploy.py deploy
```

### Production Cluster
```bash
# Configure cluster.yaml for your cloud provider
ray up cluster.yaml

# Deploy to cluster
ray submit cluster.yaml scripts/deploy.py deploy
```

### Autoscaling
```bash
# Run custom autoscaler
python scripts/autoscaler.py --min-nodes 1 --max-nodes 10
```

## Monitoring

- **Ray Dashboard**: http://localhost:8265
- **Service Health**: http://localhost:8000/health
- **Service Status**: `python scripts/deploy.py status`

## Data Sources

Supported data sources:

- **Binance**: Cryptocurrency data (WebSocket + REST)
- **Alpha Vantage**: Stock market data
- **Yahoo Finance**: Market indices and stocks
- **Forex API**: Foreign exchange rates

Configure API keys in `.env` file.

## Troubleshooting

### Common Issues

1. **Ray cluster not starting**: Check port availability (6379, 8265)
2. **Service deployment fails**: Verify dependencies and configuration
3. **API requests timeout**: Check service replica count and resource allocation

### Logs

```bash
# Check Ray logs
ray logs

# Check service status
python scripts/deploy.py status

# Debug mode
export LOG_LEVEL=DEBUG
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure code quality checks pass
5. Submit a pull request

## License

[Your License Here]

## Support

For questions and support:
- Create an issue on GitHub
- Check the Ray documentation: https://docs.ray.io/
- Ray Serve guide: https://docs.ray.io/en/latest/serve/

---

**Note**: This is a development setup. For production use, ensure proper security, monitoring, and resource management configurations.

## Infrastructure Components
- **PostgreSQL**: Persistent data storage for service state and metrics
- **Redis**: Caching and session storage for improved performance  
- **pgAdmin**: Web-based PostgreSQL administration tool
- **Redis Commander**: Web-based Redis administration tool
