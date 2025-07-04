"""
Algorunner Business Logic

This module contains the core business logic for the algorunner service.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class AlgorunnerLogic:
    """
    Core business logic for the algorunner service.
    
    This class handles algorithm execution, management, and monitoring.
    """
    
    def __init__(self):
        """Initialize the algorunner logic."""
        self.running_algorithms: Dict[str, Dict[str, Any]] = {}
        self.algorithm_history: List[Dict[str, Any]] = []
        self.available_algorithms = [
            {
                "id": "momentum_strategy",
                "name": "Momentum Trading Strategy",
                "description": "A simple momentum-based trading algorithm"
            },
            {
                "id": "mean_reversion",
                "name": "Mean Reversion Strategy", 
                "description": "Algorithm that trades on mean reversion patterns"
            },
            {
                "id": "arbitrage_scanner",
                "name": "Arbitrage Scanner",
                "description": "Scans for arbitrage opportunities across exchanges"
            }
        ]
        logger.info("Algorunner logic initialized")
    
    async def execute_algorithm(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a trading algorithm.
        
        Args:
            request_data: Dictionary containing algorithm parameters
            
        Returns:
            Dictionary containing execution results
        """
        algorithm_id = request_data.get("algorithm_id")
        parameters = request_data.get("parameters", {})
        
        if not algorithm_id:
            raise ValueError("algorithm_id is required")
        
        # Check if algorithm exists
        if not any(algo["id"] == algorithm_id for algo in self.available_algorithms):
            raise ValueError(f"Algorithm {algorithm_id} not found")
        
        # Generate execution ID
        execution_id = str(uuid.uuid4())
        
        # Store algorithm execution info
        execution_info = {
            "execution_id": execution_id,
            "algorithm_id": algorithm_id,
            "parameters": parameters,
            "start_time": datetime.now().isoformat(),
            "status": "running"
        }
        
        self.running_algorithms[execution_id] = execution_info
        
        # Simulate algorithm execution (replace with actual algorithm logic)
        try:
            result = await self._simulate_algorithm_execution(algorithm_id, parameters)
            execution_info["status"] = "completed"
            execution_info["end_time"] = datetime.now().isoformat()
            execution_info["result"] = result
            
            # Move to history
            self.algorithm_history.append(execution_info.copy())
            del self.running_algorithms[execution_id]
            
            return {
                "execution_id": execution_id,
                "algorithm_id": algorithm_id,
                "result": result,
                "status": "completed"
            }
            
        except Exception as e:
            execution_info["status"] = "failed"
            execution_info["error"] = str(e)
            execution_info["end_time"] = datetime.now().isoformat()
            
            # Move to history
            self.algorithm_history.append(execution_info.copy())
            del self.running_algorithms[execution_id]
            
            raise e
    
    async def _simulate_algorithm_execution(
        self, 
        algorithm_id: str, 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Simulate algorithm execution (replace with actual algorithm logic).
        
        Args:
            algorithm_id: ID of the algorithm to execute
            parameters: Algorithm parameters
            
        Returns:
            Dictionary containing algorithm results
        """
        # Simulate processing time
        await asyncio.sleep(2)
        
        # Simulate different results based on algorithm type
        if algorithm_id == "momentum_strategy":
            return {
                "trades_executed": 15,
                "profit_loss": 1250.75,
                "win_rate": 0.73,
                "max_drawdown": -125.50
            }
        elif algorithm_id == "mean_reversion":
            return {
                "trades_executed": 8,
                "profit_loss": 890.25,
                "win_rate": 0.625,
                "max_drawdown": -67.30
            }
        elif algorithm_id == "arbitrage_scanner":
            return {
                "opportunities_found": 23,
                "trades_executed": 12,
                "profit_loss": 2100.80,
                "total_volume": 150000
            }
        else:
            return {
                "message": f"Algorithm {algorithm_id} executed successfully",
                "execution_time": "2.1s"
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get the current status of the algorunner service.
        
        Returns:
            Dictionary containing service status
        """
        return {
            "service": "algorunner",
            "status": "healthy",
            "running_algorithms": len(self.running_algorithms),
            "total_executions": len(self.algorithm_history),
            "available_algorithms": len(self.available_algorithms),
            "uptime": "operational"
        }
    
    def get_available_algorithms(self) -> List[Dict[str, Any]]:
        """
        Get list of available algorithms.
        
        Returns:
            List of available algorithms
        """
        return self.available_algorithms.copy()
    
    async def stop_algorithm(self, execution_id: str) -> Dict[str, Any]:
        """
        Stop a running algorithm.
        
        Args:
            execution_id: ID of the algorithm execution to stop
            
        Returns:
            Dictionary containing stop operation result
        """
        if execution_id not in self.running_algorithms:
            raise ValueError(f"Algorithm execution {execution_id} not found or not running")
        
        # Update status
        execution_info = self.running_algorithms[execution_id]
        execution_info["status"] = "stopped"
        execution_info["end_time"] = datetime.now().isoformat()
        
        # Move to history
        self.algorithm_history.append(execution_info.copy())
        del self.running_algorithms[execution_id]
        
        return {
            "execution_id": execution_id,
            "status": "stopped",
            "message": "Algorithm execution stopped successfully"
        }
    
    def get_running_algorithms(self) -> Dict[str, Dict[str, Any]]:
        """
        Get currently running algorithms.
        
        Returns:
            Dictionary of running algorithms
        """
        return self.running_algorithms.copy()
    
    def get_algorithm_history(self) -> List[Dict[str, Any]]:
        """
        Get algorithm execution history.
        
        Returns:
            List of algorithm execution history
        """
        return self.algorithm_history.copy()
