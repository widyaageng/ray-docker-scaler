"""
Central Router for Ray Serve Application

This module implements the main FastAPI router that routes requests
to appropriate microservices.
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import ray
from ray.serve.handle import DeploymentHandle
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def create_router(
    algorunner_handle: DeploymentHandle,
    screener_handle: DeploymentHandle,
    tickscrawler_handle: DeploymentHandle
) -> FastAPI:
    """
    Create the main FastAPI router with all service endpoints.
    
    Args:
        algorunner_handle: Handle to the algorunner service
        screener_handle: Handle to the screener service
        tickscrawler_handle: Handle to the tickscrawler service
    
    Returns:
        FastAPI application instance
    """
    app = FastAPI(
        title="Ray Cluster Services API",
        description="Central API gateway for all microservices",
        version="1.0.0"
    )
    
    @app.get("/")
    async def root():
        """Health check endpoint."""
        return {"message": "Ray Cluster Services API is running", "status": "healthy"}
    
    @app.get("/health")
    async def health_check():
        """Detailed health check for all services."""
        try:
            # You can add health checks for individual services here
            return {
                "status": "healthy",
                "services": {
                    "algorunner": "running",
                    "screener": "running", 
                    "tickscrawler": "running"
                }
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return JSONResponse(
                status_code=500,
                content={"status": "unhealthy", "error": str(e)}
            )
    
    # Algorunner service routes
    @app.post("/api/algorunner/run")
    async def run_algorithm(request: Request):
        """Route requests to algorunner service."""
        try:
            body = await request.json()
            result = await algorunner_handle.run_algorithm.remote(body) # type: ignore
            return result
        except Exception as e:
            logger.error(f"Algorunner error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/algorunner/status")
    async def algorunner_status():
        """Get algorunner service status."""
        try:
            result = await algorunner_handle.get_status.remote() # type: ignore
            return result
        except Exception as e:
            logger.error(f"Algorunner status error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Screener service routes
    @app.post("/api/screener/screen")
    async def screen_data(request: Request):
        """Route requests to screener service."""
        try:
            body = await request.json()
            result = await screener_handle.screen.remote(body) # type: ignore
            return result
        except Exception as e:
            logger.error(f"Screener error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/screener/filters")
    async def get_filters():
        """Get available filters from screener service."""
        try:
            result = await screener_handle.get_filters.remote() # type: ignore
            return result
        except Exception as e:
            logger.error(f"Screener filters error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Tickscrawler service routes
    @app.post("/api/tickscrawler/crawl")
    async def crawl_ticks(request: Request):
        """Route requests to tickscrawler service."""
        try:
            body = await request.json()
            result = await tickscrawler_handle.crawl.remote(body) # type: ignore
            return result
        except Exception as e:
            logger.error(f"Tickscrawler error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/tickscrawler/sources")
    async def get_data_sources():
        """Get available data sources from tickscrawler service."""
        try:
            result = await tickscrawler_handle.get_sources.remote() # type: ignore
            return result
        except Exception as e:
            logger.error(f"Tickscrawler sources error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return app
