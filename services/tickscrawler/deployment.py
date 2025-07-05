"""
Tickscrawler Ray Serve Deployment

This module defines the Ray Serve deployment for the tickscrawler service.
"""

import ray
from ray import serve
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

try:
    from .logic import TickscrawlerLogic
    from .config import TICKSCRAWLER_SERVICE_CONFIG
except ImportError as e:
    import sys
    if '/workspace' not in sys.path:
        sys.path.insert(0, '/workspace')
        logger.info("Added '/workspace' to sys.path for internal imports")
    from services.tickscrawler.logic import TickscrawlerLogic
    from services.tickscrawler.config import TICKSCRAWLER_SERVICE_CONFIG


@serve.deployment(
    name="tickscrawler",
    max_ongoing_requests=TICKSCRAWLER_SERVICE_CONFIG.max_ongoing_requests,
    autoscaling_config={
        "min_replicas": TICKSCRAWLER_SERVICE_CONFIG.min_replicas,
        "max_replicas": TICKSCRAWLER_SERVICE_CONFIG.max_replicas,
        "target_ongoing_requests": TICKSCRAWLER_SERVICE_CONFIG.target_num_ongoing_requests_per_replica,
        "scale_up_delay_s": TICKSCRAWLER_SERVICE_CONFIG.scale_up_delay_s,
        "scale_down_delay_s": TICKSCRAWLER_SERVICE_CONFIG.scale_down_delay_s
    },
    ray_actor_options=TICKSCRAWLER_SERVICE_CONFIG.ray_actor_options
)
class TickscrawlerDeployment:
    """
    Ray Serve deployment for the tickscrawler service.
    
    This deployment handles requests for crawling and collecting market tick data
    from various data sources.
    """
    
    def __init__(self):
        """Initialize the tickscrawler deployment."""
        self.logic = TickscrawlerLogic()
        logger.info("Tickscrawler deployment initialized")
    
    async def crawl(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crawl market tick data based on provided parameters.
        
        Args:
            request_data: Dictionary containing crawling parameters
            
        Returns:
            Dictionary containing crawled data results
        """
        try:
            logger.info(f"Crawling data with parameters: {request_data}")
            result = await self.logic.crawl_data(request_data)
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Error crawling data: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_sources(self) -> Dict[str, Any]:
        """
        Get available data sources for crawling.
        
        Returns:
            Dictionary containing available data sources
        """
        try:
            sources = self.logic.get_available_sources()
            return {"status": "success", "sources": sources}
        except Exception as e:
            logger.error(f"Error getting sources: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the tickscrawler service.
        
        Returns:
            Dictionary containing service status information
        """
        try:
            status = self.logic.get_service_status()
            return {"status": "success", "data": status}
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {"status": "error", "error": str(e)}
    
    async def start_streaming(self, stream_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start streaming tick data from a source.
        
        Args:
            stream_config: Dictionary containing streaming configuration
            
        Returns:
            Dictionary containing streaming setup result
        """
        try:
            result = await self.logic.start_streaming(stream_config)
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Error starting stream: {e}")
            return {"status": "error", "error": str(e)}
    
    async def stop_streaming(self, stream_id: str) -> Dict[str, Any]:
        """
        Stop a streaming connection.
        
        Args:
            stream_id: ID of the stream to stop
            
        Returns:
            Dictionary containing stop operation result
        """
        try:
            result = await self.logic.stop_streaming(stream_id)
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Error stopping stream {stream_id}: {e}")
            return {"status": "error", "error": str(e)}
    
    async def get_historical_data(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get historical tick data.
        
        Args:
            request_data: Dictionary containing historical data request
            
        Returns:
            Dictionary containing historical data
        """
        try:
            result = await self.logic.get_historical_data(request_data)
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return {"status": "error", "error": str(e)}
