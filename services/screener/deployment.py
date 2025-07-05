"""
Screener Ray Serve Deployment

This module defines the Ray Serve deployment for the screener service.
"""

import ray
from ray import serve
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

try:
    from .logic import ScreenerLogic
    from .config import SCREENER_SERVICE_CONFIG
except ImportError as e:
    import sys
    if '/workspace' not in sys.path:
        sys.path.insert(0, '/workspace')
        logger.info("Added '/workspace' to sys.path for internal imports")
    from services.screener.logic import ScreenerLogic
    from services.screener.config import SCREENER_SERVICE_CONFIG



@serve.deployment(
    name="screener",
    max_ongoing_requests=SCREENER_SERVICE_CONFIG.max_ongoing_requests,
    autoscaling_config={
        "min_replicas": SCREENER_SERVICE_CONFIG.min_replicas,
        "max_replicas": SCREENER_SERVICE_CONFIG.max_replicas,
        "target_ongoing_requests": SCREENER_SERVICE_CONFIG.target_num_ongoing_requests_per_replica,
        "scale_up_delay_s": SCREENER_SERVICE_CONFIG.scale_up_delay_s,
        "scale_down_delay_s": SCREENER_SERVICE_CONFIG.scale_down_delay_s
    },
    ray_actor_options=SCREENER_SERVICE_CONFIG.ray_actor_options
)
class ScreenerDeployment:
    """
    Ray Serve deployment for the screener service.
    
    This deployment handles requests for screening and filtering financial data
    based on various criteria.
    """
    
    def __init__(self):
        """Initialize the screener deployment."""
        self.logic = ScreenerLogic()
        logger.info("Screener deployment initialized")
    
    async def screen(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Screen financial data based on provided filters.
        
        Args:
            request_data: Dictionary containing screening criteria
            
        Returns:
            Dictionary containing screening results
        """
        try:
            logger.info(f"Screening data with criteria: {request_data}")
            result = await self.logic.screen_data(request_data)
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Error screening data: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_filters(self) -> Dict[str, Any]:
        """
        Get available screening filters.
        
        Returns:
            Dictionary containing available filters
        """
        try:
            filters = self.logic.get_available_filters()
            return {"status": "success", "filters": filters}
        except Exception as e:
            logger.error(f"Error getting filters: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the screener service.
        
        Returns:
            Dictionary containing service status information
        """
        try:
            status = self.logic.get_service_status()
            return {"status": "success", "data": status}
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def create_custom_filter(self, filter_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a custom screening filter.
        
        Args:
            filter_data: Dictionary containing filter definition
            
        Returns:
            Dictionary containing creation result
        """
        try:
            result = await self.logic.create_custom_filter(filter_data)
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Error creating custom filter: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_market_overview(self) -> Dict[str, Any]:
        """
        Get market overview data.
        
        Returns:
            Dictionary containing market overview
        """
        try:
            overview = await self.logic.get_market_overview()
            return {"status": "success", "overview": overview}
        except Exception as e:
            logger.error(f"Error getting market overview: {e}")
            return {"status": "error", "error": str(e)}
