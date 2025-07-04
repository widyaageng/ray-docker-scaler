# Infrastructure Setup

This document describes the infrastructure components for the Ray Cluster project.

## Components

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

### Admin Tools

#### pgAdmin (PostgreSQL Admin)
- **Image**: dpage/pgadmin4
- **Container**: ray-pgadmin
- **Port**: 8080
- **URL**: http://localhost:8080
- **Email**: admin@raycluster.com
- **Password**: admin

#### Redis Commander (Redis Admin)
- **Image**: rediscommander/redis-commander
- **Container**: ray-redis-commander
- **Port**: 8081
- **URL**: http://localhost:8081
- **Username**: admin
- **Password**: admin

## Usage

### Start Infrastructure
```bash
python scripts/infra.py start
```

### Stop Infrastructure
```bash
python scripts/infra.py stop
```

### Check Status
```bash
python scripts/infra.py status
```

### View Logs
```bash
# All services
python scripts/infra.py logs

# Specific service
python scripts/infra.py logs --service postgres

# Follow logs
python scripts/infra.py logs --service redis --follow
```

### Connection Information
```bash
python scripts/infra.py info
```

### Clean Up (Remove all data)
```bash
python scripts/infra.py cleanup
```

## Database Schema

The database is automatically initialized with:

- **Schemas**: algorunner, screener, tickscrawler, shared
- **Extensions**: uuid-ossp, pg_stat_statements, pg_trgm, btree_gin, btree_gist
- **Tables**: Pre-created tables for all services with proper indexes
- **Sample Data**: Initial algorithms and data sources

## Configuration

### Environment Variables
All configuration is managed through the `.env` file:

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

REDIS_COMMANDER_USER=admin
REDIS_COMMANDER_PASSWORD=admin
REDIS_COMMANDER_PORT=8081
```

### Volume Mounts
- **PostgreSQL Data**: `./postgres/data`
- **PostgreSQL Config**: `./postgres/config`
- **PostgreSQL Init Scripts**: `./postgres/init`
- **Redis Data**: `./redis/data`
- **Redis Config**: `./redis/config`

## Network

All services run on the `ray-cluster` Docker network with subnet `172.20.0.0/16`.

## Health Checks

Both PostgreSQL and Redis have health checks configured:
- **PostgreSQL**: `pg_isready` check every 10 seconds
- **Redis**: Redis ping check every 10 seconds

## Performance Tuning

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
2. Restart infrastructure: `python scripts/infra.py restart`

## Troubleshooting

### Common Issues

1. **Port conflicts**: Check if ports 5432, 6379, 8080, 8081 are available
2. **Permission issues**: Ensure Docker has proper permissions
3. **Data corruption**: Use `python scripts/infra.py cleanup` to reset

### Logs
Check service logs for debugging:
```bash
python scripts/infra.py logs --service postgres --follow
python scripts/infra.py logs --service redis --follow
```

### Database Connection Test
```bash
# Test PostgreSQL connection
docker exec -it ray-postgres psql -U rayuser -d raycluster -c "SELECT version();"

# Test Redis connection
docker exec -it ray-redis redis-cli -a redispassword ping
```
