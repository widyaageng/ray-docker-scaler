"""
Integration tests for the Ray cluster services.
"""

import pytest
import asyncio
import sys
import os
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import ray
from ray import serve

# Import service deployments
from services.algorunner.deployment import AlgorunnerDeployment
from services.screener.deployment import ScreenerDeployment
from services.tickscrawler.deployment import TickscrawlerDeployment


class TestServiceIntegration:
    """Integration tests for all services."""
    
    @classmethod
    def setup_class(cls):
        """Set up Ray cluster for testing."""
        if not ray.is_initialized():
            ray.init(ignore_reinit_error=True)
        
        if not serve.status().applications:
            serve.start()
    
    @classmethod
    def teardown_class(cls):
        """Clean up Ray cluster after testing."""
        try:
            serve.shutdown()
        except Exception:
            pass
        
        try:
            ray.shutdown()
        except Exception:
            pass
    
    def test_algorunner_service_health(self):
        """Test algorunner service health."""
        deployment = AlgorunnerDeployment()
        
        # Test that the deployment can be created
        assert deployment is not None
        assert hasattr(deployment, 'logic')
    
    def test_screener_service_health(self):
        """Test screener service health."""
        deployment = ScreenerDeployment()
        
        # Test that the deployment can be created
        assert deployment is not None
        assert hasattr(deployment, 'logic')
    
    def test_tickscrawler_service_health(self):
        """Test tickscrawler service health."""
        deployment = TickscrawlerDeployment()
        
        # Test that the deployment can be created
        assert deployment is not None
        assert hasattr(deployment, 'logic')
    
    @pytest.mark.asyncio
    async def test_algorunner_workflow(self):
        """Test a complete algorunner workflow."""
        deployment = AlgorunnerDeployment()
        
        # Test getting status
        status_result = await deployment.get_status()
        assert status_result["status"] == "success"
        
        # Test listing algorithms
        algo_result = await deployment.list_algorithms()
        assert algo_result["status"] == "success"
        assert len(algo_result["algorithms"]) > 0
        
        # Test running an algorithm
        run_request = {
            "algorithm_id": "momentum_strategy",
            "parameters": {"symbol": "AAPL", "period": 14}
        }
        
        run_result = await deployment.run_algorithm(run_request)
        assert run_result["status"] == "success"
        assert "result" in run_result
        assert "execution_id" in run_result["result"]
    
    @pytest.mark.asyncio
    async def test_screener_workflow(self):
        """Test a complete screener workflow."""
        deployment = ScreenerDeployment()
        
        # Test getting status
        status_result = await deployment.get_status()
        assert status_result["status"] == "success"
        
        # Test getting filters
        filters_result = await deployment.get_filters()
        assert filters_result["status"] == "success"
        assert len(filters_result["filters"]) > 0
        
        # Test screening data
        screen_request = {
            "filters": [
                {
                    "type": "price_filter",
                    "parameters": {"min_price": 100, "max_price": 300}
                }
            ],
            "limit": 10
        }
        
        screen_result = await deployment.screen(screen_request)
        assert screen_result["status"] == "success"
        assert "result" in screen_result
        assert "stocks" in screen_result["result"]
        
        # Test market overview
        overview_result = await deployment.get_market_overview()
        assert overview_result["status"] == "success"
        assert "overview" in overview_result
    
    @pytest.mark.asyncio
    async def test_tickscrawler_workflow(self):
        """Test a complete tickscrawler workflow."""
        deployment = TickscrawlerDeployment()
        
        # Test getting status
        status_result = await deployment.get_status()
        assert status_result["status"] == "success"
        
        # Test getting sources
        sources_result = await deployment.get_sources()
        assert sources_result["status"] == "success"
        assert len(sources_result["sources"]) > 0
        
        # Test crawling data
        crawl_request = {
            "source_id": "binance",
            "symbols": ["BTCUSDT"],
            "data_type": "ticks",
            "limit": 10
        }
        
        crawl_result = await deployment.crawl(crawl_request)
        assert crawl_result["status"] == "success"
        assert "result" in crawl_result
        assert "data" in crawl_result["result"]
        
        # Test starting a stream
        stream_request = {
            "source_id": "binance",
            "symbols": ["BTCUSDT", "ETHUSDT"]
        }
        
        stream_result = await deployment.start_streaming(stream_request)
        assert stream_result["status"] == "success"
        assert "result" in stream_result
        
        stream_id = stream_result["result"]["stream_id"]
        
        # Test stopping the stream
        stop_result = await deployment.stop_streaming(stream_id)
        assert stop_result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_cross_service_compatibility(self):
        """Test that services can work together."""
        algo_deployment = AlgorunnerDeployment()
        screener_deployment = ScreenerDeployment()
        
        # Get market data from screener
        screen_request = {
            "filters": [
                {
                    "type": "price_filter",
                    "parameters": {"min_price": 100}
                }
            ],
            "limit": 5
        }
        
        screen_result = await screener_deployment.screen(screen_request)
        assert screen_result["status"] == "success"
        
        stocks = screen_result["result"]["stocks"]
        assert len(stocks) > 0
        
        # Use the first stock symbol in an algorithm
        symbol = stocks[0]["symbol"]
        
        algo_request = {
            "algorithm_id": "momentum_strategy",
            "parameters": {"symbol": symbol, "period": 14}
        }
        
        algo_result = await algo_deployment.run_algorithm(algo_request)
        assert algo_result["status"] == "success"
        assert "result" in algo_result
        
        # Both services should be able to work with the same symbol
        execution_result = algo_result["result"]["result"]
        assert "trades_executed" in execution_result
    
    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling across services."""
        algo_deployment = AlgorunnerDeployment()
        screener_deployment = ScreenerDeployment()
        tickscrawler_deployment = TickscrawlerDeployment()
        
        # Test algorunner with invalid algorithm
        invalid_algo_request = {
            "algorithm_id": "invalid_algorithm",
            "parameters": {}
        }
        
        algo_result = await algo_deployment.run_algorithm(invalid_algo_request)
        assert algo_result["status"] == "error"
        assert "error" in algo_result
        
        # Test tickscrawler with invalid source
        invalid_crawl_request = {
            "source_id": "invalid_source",
            "symbols": ["BTCUSDT"],
            "limit": 10
        }
        
        crawl_result = await tickscrawler_deployment.crawl(invalid_crawl_request)
        assert crawl_result["status"] == "error"
        assert "error" in crawl_result
        
        # Test screener with valid request (should still work)
        valid_screen_request = {
            "filters": [],
            "limit": 5
        }
        
        screen_result = await screener_deployment.screen(valid_screen_request)
        assert screen_result["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent operations across services."""
        algo_deployment = AlgorunnerDeployment()
        screener_deployment = ScreenerDeployment()
        tickscrawler_deployment = TickscrawlerDeployment()
        
        # Create concurrent tasks
        tasks = []
        
        # Algorunner task
        algo_task = algo_deployment.run_algorithm({
            "algorithm_id": "momentum_strategy",
            "parameters": {"symbol": "AAPL"}
        })
        tasks.append(algo_task)
        
        # Screener task
        screen_task = screener_deployment.screen({
            "filters": [{"type": "price_filter", "parameters": {"min_price": 50}}],
            "limit": 10
        })
        tasks.append(screen_task)
        
        # Tickscrawler task
        crawl_task = tickscrawler_deployment.crawl({
            "source_id": "binance",
            "symbols": ["BTCUSDT"],
            "limit": 5
        })
        tasks.append(crawl_task)
        
        # Execute all tasks concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check that all tasks completed successfully
        for result in results:
            if isinstance(result, Exception):
                pytest.fail(f"Concurrent task failed with exception: {result}")
            else:
                assert result["status"] == "success"
    
    def test_service_configurations(self):
        """Test that service configurations are properly loaded."""
        from services.algorunner.config import ALGORUNNER_SERVICE_CONFIG
        from services.screener.config import SCREENER_SERVICE_CONFIG
        from services.tickscrawler.config import TICKSCRAWLER_SERVICE_CONFIG
        
        # Test algorunner config
        assert ALGORUNNER_SERVICE_CONFIG.name == "algorunner"
        assert ALGORUNNER_SERVICE_CONFIG.num_replicas > 0
        assert ALGORUNNER_SERVICE_CONFIG.max_concurrent_queries > 0
        
        # Test screener config
        assert SCREENER_SERVICE_CONFIG.name == "screener"
        assert SCREENER_SERVICE_CONFIG.num_replicas > 0
        assert SCREENER_SERVICE_CONFIG.max_concurrent_queries > 0
        
        # Test tickscrawler config
        assert TICKSCRAWLER_SERVICE_CONFIG.name == "tickscrawler"
        assert TICKSCRAWLER_SERVICE_CONFIG.num_replicas > 0
        assert TICKSCRAWLER_SERVICE_CONFIG.max_concurrent_queries > 0


if __name__ == "__main__":
    pytest.main([__file__])
