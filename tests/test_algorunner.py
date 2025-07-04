"""
Unit tests for the Algorunner service.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.algorunner.logic import AlgorunnerLogic
from services.algorunner.deployment import AlgorunnerDeployment


class TestAlgorunnerLogic:
    """Test cases for AlgorunnerLogic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.logic = AlgorunnerLogic()
    
    def test_initialization(self):
        """Test logic initialization."""
        assert self.logic.running_algorithms == {}
        assert self.logic.algorithm_history == []
        assert len(self.logic.available_algorithms) > 0
    
    def test_get_available_algorithms(self):
        """Test getting available algorithms."""
        algorithms = self.logic.get_available_algorithms()
        assert isinstance(algorithms, list)
        assert len(algorithms) > 0
        
        for algo in algorithms:
            assert "id" in algo
            assert "name" in algo
            assert "description" in algo
    
    @pytest.mark.asyncio
    async def test_execute_algorithm_success(self):
        """Test successful algorithm execution."""
        request_data = {
            "algorithm_id": "momentum_strategy",
            "parameters": {"symbol": "AAPL", "period": 14}
        }
        
        result = await self.logic.execute_algorithm(request_data)
        
        assert "execution_id" in result
        assert "algorithm_id" in result
        assert result["algorithm_id"] == "momentum_strategy"
        assert result["status"] == "completed"
        assert "result" in result
        
        # Check that it was added to history
        assert len(self.logic.algorithm_history) == 1
    
    @pytest.mark.asyncio
    async def test_execute_algorithm_missing_id(self):
        """Test algorithm execution with missing algorithm_id."""
        request_data = {"parameters": {"symbol": "AAPL"}}
        
        with pytest.raises(ValueError, match="algorithm_id is required"):
            await self.logic.execute_algorithm(request_data)
    
    @pytest.mark.asyncio
    async def test_execute_algorithm_invalid_id(self):
        """Test algorithm execution with invalid algorithm_id."""
        request_data = {
            "algorithm_id": "invalid_algorithm",
            "parameters": {"symbol": "AAPL"}
        }
        
        with pytest.raises(ValueError, match="Algorithm invalid_algorithm not found"):
            await self.logic.execute_algorithm(request_data)
    
    def test_get_service_status(self):
        """Test getting service status."""
        status = self.logic.get_service_status()
        
        assert status["service"] == "algorunner"
        assert status["status"] == "healthy"
        assert "running_algorithms" in status
        assert "total_executions" in status
        assert "available_algorithms" in status
    
    @pytest.mark.asyncio
    async def test_stop_algorithm(self):
        """Test stopping a running algorithm."""
        # First, start an algorithm
        request_data = {
            "algorithm_id": "momentum_strategy",
            "parameters": {"symbol": "AAPL"}
        }
        
        # Mock the simulation to make it hang so we can stop it
        with patch.object(self.logic, '_simulate_algorithm_execution') as mock_sim:
            # Create a future that never completes
            future = asyncio.Future()
            mock_sim.return_value = future
            
            # Start the algorithm (but don't await it)
            task = asyncio.create_task(self.logic.execute_algorithm(request_data))
            
            # Give it a moment to start
            await asyncio.sleep(0.1)
            
            # Check that it's in running algorithms
            assert len(self.logic.running_algorithms) == 1
            execution_id = list(self.logic.running_algorithms.keys())[0]
            
            # Stop the algorithm
            result = await self.logic.stop_algorithm(execution_id)
            
            assert result["execution_id"] == execution_id
            assert result["status"] == "stopped"
            
            # Check that it's no longer running
            assert len(self.logic.running_algorithms) == 0
            assert len(self.logic.algorithm_history) == 1
            
            # Cancel the task to clean up
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    
    @pytest.mark.asyncio
    async def test_stop_nonexistent_algorithm(self):
        """Test stopping a non-existent algorithm."""
        with pytest.raises(ValueError, match="Algorithm execution .* not found"):
            await self.logic.stop_algorithm("non_existent_id")
    
    @pytest.mark.asyncio
    async def test_simulate_algorithm_execution(self):
        """Test algorithm simulation."""
        # Test momentum strategy
        result = await self.logic._simulate_algorithm_execution(
            "momentum_strategy", 
            {"symbol": "AAPL"}
        )
        
        assert "trades_executed" in result
        assert "profit_loss" in result
        assert "win_rate" in result
        assert "max_drawdown" in result
        
        # Test mean reversion
        result = await self.logic._simulate_algorithm_execution(
            "mean_reversion", 
            {"symbol": "AAPL"}
        )
        
        assert "trades_executed" in result
        assert "profit_loss" in result
        assert "win_rate" in result
        assert "max_drawdown" in result
        
        # Test arbitrage scanner
        result = await self.logic._simulate_algorithm_execution(
            "arbitrage_scanner", 
            {"symbol": "AAPL"}
        )
        
        assert "opportunities_found" in result
        assert "trades_executed" in result
        assert "profit_loss" in result
        assert "total_volume" in result


class TestAlgorunnerDeployment:
    """Test cases for AlgorunnerDeployment."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.deployment = AlgorunnerDeployment()
    
    def test_initialization(self):
        """Test deployment initialization."""
        assert hasattr(self.deployment, 'logic')
        assert isinstance(self.deployment.logic, AlgorunnerLogic)
    
    @pytest.mark.asyncio
    async def test_run_algorithm_success(self):
        """Test successful algorithm run through deployment."""
        request_data = {
            "algorithm_id": "momentum_strategy",
            "parameters": {"symbol": "AAPL", "period": 14}
        }
        
        result = await self.deployment.run_algorithm(request_data)
        
        assert result["status"] == "success"
        assert "result" in result
        assert "execution_id" in result["result"]
    
    @pytest.mark.asyncio
    async def test_run_algorithm_error(self):
        """Test algorithm run with error."""
        request_data = {
            "algorithm_id": "invalid_algorithm",
            "parameters": {"symbol": "AAPL"}
        }
        
        result = await self.deployment.run_algorithm(request_data)
        
        assert result["status"] == "error"
        assert "error" in result
    
    @pytest.mark.asyncio
    async def test_get_status(self):
        """Test getting deployment status."""
        result = await self.deployment.get_status()
        
        assert result["status"] == "success"
        assert "data" in result
        assert result["data"]["service"] == "algorunner"
    
    @pytest.mark.asyncio
    async def test_list_algorithms(self):
        """Test listing available algorithms."""
        result = await self.deployment.list_algorithms()
        
        assert result["status"] == "success"
        assert "algorithms" in result
        assert len(result["algorithms"]) > 0
    
    @pytest.mark.asyncio
    async def test_stop_algorithm_error(self):
        """Test stopping non-existent algorithm."""
        result = await self.deployment.stop_algorithm("non_existent_id")
        
        assert result["status"] == "error"
        assert "error" in result


if __name__ == "__main__":
    pytest.main([__file__])
