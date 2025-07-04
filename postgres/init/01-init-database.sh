#!/bin/bash
set -e

# Create database for Ray Cluster services
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Create extensions
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";
    CREATE EXTENSION IF NOT EXISTS "pg_trgm";
    CREATE EXTENSION IF NOT EXISTS "btree_gin";
    CREATE EXTENSION IF NOT EXISTS "btree_gist";

    -- Create schemas for different services
    CREATE SCHEMA IF NOT EXISTS algorunner;
    CREATE SCHEMA IF NOT EXISTS screener;
    CREATE SCHEMA IF NOT EXISTS tickscrawler;
    CREATE SCHEMA IF NOT EXISTS shared;

    -- Grant permissions
    GRANT ALL ON SCHEMA algorunner TO $POSTGRES_USER;
    GRANT ALL ON SCHEMA screener TO $POSTGRES_USER;
    GRANT ALL ON SCHEMA tickscrawler TO $POSTGRES_USER;
    GRANT ALL ON SCHEMA shared TO $POSTGRES_USER;

    -- Create tables for shared models
    CREATE TABLE IF NOT EXISTS shared.service_metrics (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        service_name VARCHAR(100) NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        cpu_usage DECIMAL(5,2),
        memory_usage DECIMAL(5,2),
        request_count INTEGER,
        error_count INTEGER,
        avg_response_time DECIMAL(10,3),
        active_connections INTEGER,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS shared.service_health (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        service_name VARCHAR(100) NOT NULL,
        status VARCHAR(20) NOT NULL,
        uptime DECIMAL(15,3),
        last_check TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        details JSONB,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    -- Create tables for algorunner service
    CREATE TABLE IF NOT EXISTS algorunner.algorithms (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        algorithm_id VARCHAR(100) UNIQUE NOT NULL,
        name VARCHAR(200) NOT NULL,
        description TEXT,
        parameters JSONB DEFAULT '{}',
        enabled BOOLEAN DEFAULT true,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS algorunner.executions (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        execution_id VARCHAR(100) UNIQUE NOT NULL,
        algorithm_id VARCHAR(100) NOT NULL,
        status VARCHAR(50) NOT NULL,
        start_time TIMESTAMPTZ NOT NULL,
        end_time TIMESTAMPTZ,
        parameters JSONB DEFAULT '{}',
        result JSONB,
        error_message TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    -- Create tables for screener service
    CREATE TABLE IF NOT EXISTS screener.filters (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        filter_id VARCHAR(100) UNIQUE NOT NULL,
        name VARCHAR(200) NOT NULL,
        description TEXT,
        filter_type VARCHAR(100) NOT NULL,
        parameters JSONB DEFAULT '{}',
        enabled BOOLEAN DEFAULT true,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS screener.screening_results (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        request_id VARCHAR(100) NOT NULL,
        filters_applied JSONB NOT NULL,
        total_stocks INTEGER NOT NULL,
        filtered_count INTEGER NOT NULL,
        execution_time DECIMAL(10,3),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    -- Create tables for tickscrawler service
    CREATE TABLE IF NOT EXISTS tickscrawler.data_sources (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        source_id VARCHAR(100) UNIQUE NOT NULL,
        name VARCHAR(200) NOT NULL,
        source_type VARCHAR(100) NOT NULL,
        description TEXT,
        endpoints JSONB DEFAULT '{}',
        supported_symbols TEXT[],
        enabled BOOLEAN DEFAULT true,
        rate_limit INTEGER,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS tickscrawler.crawl_jobs (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        crawl_id VARCHAR(100) UNIQUE NOT NULL,
        source_id VARCHAR(100) NOT NULL,
        symbols TEXT[] NOT NULL,
        data_type VARCHAR(50) NOT NULL,
        status VARCHAR(50) NOT NULL,
        start_time TIMESTAMPTZ NOT NULL,
        end_time TIMESTAMPTZ,
        records_count INTEGER DEFAULT 0,
        error_message TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS tickscrawler.market_data (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        symbol VARCHAR(50) NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL,
        data_type VARCHAR(50) NOT NULL,
        data JSONB NOT NULL,
        source VARCHAR(100) NOT NULL,
        crawl_id VARCHAR(100),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    -- Create indexes for better performance
    CREATE INDEX IF NOT EXISTS idx_service_metrics_service_timestamp 
        ON shared.service_metrics(service_name, timestamp);
    CREATE INDEX IF NOT EXISTS idx_service_health_service_timestamp 
        ON shared.service_health(service_name, last_check);
    
    CREATE INDEX IF NOT EXISTS idx_algorithms_algorithm_id 
        ON algorunner.algorithms(algorithm_id);
    CREATE INDEX IF NOT EXISTS idx_executions_algorithm_id 
        ON algorunner.executions(algorithm_id);
    CREATE INDEX IF NOT EXISTS idx_executions_status 
        ON algorunner.executions(status);
    CREATE INDEX IF NOT EXISTS idx_executions_start_time 
        ON algorunner.executions(start_time);
    
    CREATE INDEX IF NOT EXISTS idx_filters_filter_type 
        ON screener.filters(filter_type);
    CREATE INDEX IF NOT EXISTS idx_screening_results_created_at 
        ON screener.screening_results(created_at);
    
    CREATE INDEX IF NOT EXISTS idx_data_sources_source_id 
        ON tickscrawler.data_sources(source_id);
    CREATE INDEX IF NOT EXISTS idx_crawl_jobs_source_id 
        ON tickscrawler.crawl_jobs(source_id);
    CREATE INDEX IF NOT EXISTS idx_crawl_jobs_status 
        ON tickscrawler.crawl_jobs(status);
    CREATE INDEX IF NOT EXISTS idx_market_data_symbol_timestamp 
        ON tickscrawler.market_data(symbol, timestamp);
    CREATE INDEX IF NOT EXISTS idx_market_data_data_type 
        ON tickscrawler.market_data(data_type);
    CREATE INDEX IF NOT EXISTS idx_market_data_source 
        ON tickscrawler.market_data(source);

    -- Insert some sample data
    INSERT INTO algorunner.algorithms (algorithm_id, name, description, parameters) VALUES
        ('momentum_strategy', 'Momentum Trading Strategy', 'A simple momentum-based trading algorithm', '{"default_period": 14}'),
        ('mean_reversion', 'Mean Reversion Strategy', 'Algorithm that trades on mean reversion patterns', '{"lookback_period": 20}'),
        ('arbitrage_scanner', 'Arbitrage Scanner', 'Scans for arbitrage opportunities across exchanges', '{"threshold": 0.5}')
    ON CONFLICT (algorithm_id) DO NOTHING;

    INSERT INTO tickscrawler.data_sources (source_id, name, source_type, description, endpoints, supported_symbols) VALUES
        ('binance', 'Binance', 'cryptocurrency', 'Binance cryptocurrency exchange', '{"websocket": "wss://stream.binance.com:9443", "rest": "https://api.binance.com"}', ARRAY['BTCUSDT', 'ETHUSDT', 'ADAUSDT']),
        ('alpha_vantage', 'Alpha Vantage', 'stocks', 'Stock market data provider', '{"rest": "https://www.alphavantage.co/query"}', ARRAY['AAPL', 'GOOGL', 'MSFT']),
        ('yahoo_finance', 'Yahoo Finance', 'stocks', 'Yahoo Finance data source', '{"rest": "https://query1.finance.yahoo.com"}', ARRAY['^GSPC', '^IXIC', '^DJI'])
    ON CONFLICT (source_id) DO NOTHING;

EOSQL

echo "Database initialization completed successfully!"
