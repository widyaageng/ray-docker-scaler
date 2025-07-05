"""
Central Router Ray Serve Deployment

This module implements the main router as a Ray Serve deployment
that routes requests to appropriate microservices.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from ray import serve
from ray.serve.handle import DeploymentHandle
import logging

logger = logging.getLogger(__name__)

# Create FastAPI app outside the class
app = FastAPI(
    title="Ray Cluster Services API",
    description="Central API gateway for all microservices",
    version="1.0.0"
)


@serve.deployment(
    name="main-router",
    max_ongoing_requests=100,
    autoscaling_config={
        "min_replicas": 1,
        "max_replicas": 10,
        "target_ongoing_requests": 100,
        "scale_up_delay_s": 10,
        "scale_down_delay_s": 60
    },
    ray_actor_options={"num_cpus": 0.3, "memory": 64 * 1024 * 1024}
)
@serve.ingress(app)
class MainRouterDeployment:
    """Main router deployment that handles all incoming requests."""
    
    def __init__(self, algorunner_handle: DeploymentHandle, screener_handle: DeploymentHandle, tickscrawler_handle: DeploymentHandle):
        self.algorunner_handle = algorunner_handle
        self.screener_handle = screener_handle
        self.tickscrawler_handle = tickscrawler_handle
    
    @app.get("/")
    async def root(self):
        """Health check endpoint."""
        return {"message": "Ray Cluster Services API is running", "status": "healthy"}
    
    @app.get("/health")
    async def health_check(self):
        """Detailed health check for all services."""
        try:
            # You can add health checks for individual services here
            return {
                "status": "healthy",
                "services": {
                    "algorunner": "healthy",
                    "screener": "healthy", 
                    "tickscrawler": "healthy"
                },
                "cluster": "connected"
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse(
                status_code=503,
                content={"status": "unhealthy", "error": str(e)}
            )
    
    # Algorunner service routes
    @app.post("/api/algorunner/run")
    async def run_algorithm(self, request: Request):
        """Route requests to algorunner service."""
        try:
            body = await request.json()
            result = await self.algorunner_handle.run_algorithm.remote(body) # type: ignore
            return result
        except Exception as e:
            logger.error(f"Algorunner error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/algorunner/status")
    async def get_algorunner_status(self):
        """Get algorunner service status."""
        try:
            result = await self.algorunner_handle.get_status.remote() # type: ignore
            return result
        except Exception as e:
            logger.error(f"Algorunner status error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        
    
    @app.get("/api/screener/status")
    async def get_screener_status(self):
        """Get screener service status."""
        try:
            result = await self.screener_handle.get_status.remote() # type: ignore
            return result
        except Exception as e:
            logger.error(f"Screener status error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Screener service routes
    @app.post("/api/screener/screen")
    async def screen_data(self, request: Request):
        """Route requests to screener service."""
        try:
            body = await request.json()
            result = await self.screener_handle.screen.remote(body) # type: ignore
            return result
        except Exception as e:
            logger.error(f"Screener error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/screener/filters")
    async def get_filters(self):
        """Get available filters from screener service."""
        try:
            result = await self.screener_handle.get_filters.remote() # type: ignore
            return result
        except Exception as e:
            logger.error(f"Screener filters error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        
    @app.get("/api/tickscrawler/status")
    async def get_tickscrawler_status(self):
        """Get tickscrawler service status."""
        try:
            result = await self.tickscrawler_handle.get_status.remote() # type: ignore
            return result
        except Exception as e:
            logger.error(f"Tickscrawler status error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Tickscrawler service routes
    @app.post("/api/tickscrawler/crawl")
    async def crawl_ticks(self, request: Request):
        """Route requests to tickscrawler service."""
        try:
            body = await request.json()
            result = await self.tickscrawler_handle.crawl.remote(body) # type: ignore
            return result
        except Exception as e:
            logger.error(f"Tickscrawler error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/tickscrawler/sources")
    async def get_data_sources(self):
        """Get available data sources from tickscrawler service."""
        try:
            result = await self.tickscrawler_handle.get_sources.remote() # type: ignore
            return result
        except Exception as e:
            logger.error(f"Tickscrawler sources error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
