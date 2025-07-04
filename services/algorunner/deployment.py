"""
Algorunner Ray Serve Deployment

This module defines the Ray Serve deployment for the algorunner service.
"""

import ray
from ray import serve
from fastapi import FastAPI
from typing import Dict, Any
import logging

from .logic import AlgorunnerLogic
from .config import ALGORUNNER_SERVICE_CONFIG

logger = logging.getLogger(__name__)


@serve.deployment(
    name="algorunner",
    num_replicas=ALGORUNNER_SERVICE_CONFIG.num_replicas,
    max_ongoing_requests=ALGORUNNER_SERVICE_CONFIG.max_ongoing_requests,
    ray_actor_options=ALGORUNNER_SERVICE_CONFIG.ray_actor_options
)
class AlgorunnerDeployment:
    """
    Ray Serve deployment for the algorunner service.
    
    This deployment handles requests for running trading algorithms and
    managing algorithm execution.
    """
    
    def __init__(self):
        """Initialize the algorunner deployment."""
        self.logic = AlgorunnerLogic()
        logger.info("Algorunner deployment initialized")
    
    async def run_algorithm(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a trading algorithm with the provided parameters.
        
        Args:
            request_data: Dictionary containing algorithm parameters
            
        Returns:
            Dictionary containing algorithm execution results
        """
        try:
            logger.info(f"Running algorithm with data: {request_data}")
            result = await self.logic.execute_algorithm(request_data)
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Error running algorithm: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the algorunner service.
        
        Returns:
            Dictionary containing service status information
        """
        try:
            status = self.logic.get_service_status()
            return {"status": "success", "data": status}
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def list_algorithms(self) -> Dict[str, Any]:
        """
        List available algorithms.
        
        Returns:
            Dictionary containing list of available algorithms
        """
        try:
            algorithms = self.logic.get_available_algorithms()
            return {"status": "success", "algorithms": algorithms}
        except Exception as e:
            logger.error(f"Error listing algorithms: {e}")
            return {"status": "error", "error": str(e)}
    
    async def stop_algorithm(self, algorithm_id: str) -> Dict[str, Any]:
        """
        Stop a running algorithm.
        
        Args:
            algorithm_id: ID of the algorithm to stop
            
        Returns:
            Dictionary containing stop operation result
        """
        try:
            result = await self.logic.stop_algorithm(algorithm_id)
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Error stopping algorithm {algorithm_id}: {e}")
            return {"status": "error", "error": str(e)}
