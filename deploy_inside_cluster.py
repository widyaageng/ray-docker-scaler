#!/usr/bin/env python3
"""
Deploy services from inside the Ray cluster container.
This script avoids Python version mismatch issues.
"""

import ray
from ray import serve
import logging
import sys
import os

# Add the workspace to the Python path
sys.path.insert(0, '/workspace')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def deploy_services():
    """Deploy all Ray Serve services."""
    logger.info("Starting Ray Serve application deployment from inside cluster...")
    
    # Connect to the local Ray cluster (already running in this container)
    ray.init(address="auto", ignore_reinit_error=True)
    logger.info("Connected to Ray cluster")
    
    # Start Ray Serve
    serve.start(detached=True)
    logger.info("Ray Serve started successfully")
    
    # Import services
    from services.algorunner.deployment import AlgorunnerDeployment
    from services.screener.deployment import ScreenerDeployment
    from services.tickscrawler.deployment import TickscrawlerDeployment
    from serve_app.router_deployment import MainRouterDeployment
    
    # Deploy individual services (without HTTP routes)
    logger.info("Deploying individual services...")
    algorunner_handle = serve.run(AlgorunnerDeployment.bind(), name="algorunner", route_prefix=None)
    logger.info("✅ Algorunner service deployed")
    
    screener_handle = serve.run(ScreenerDeployment.bind(), name="screener", route_prefix=None)
    logger.info("✅ Screener service deployed")
    
    tickscrawler_handle = serve.run(TickscrawlerDeployment.bind(), name="tickscrawler", route_prefix=None)
    logger.info("✅ Tickscrawler service deployed")
    
    # Deploy the main router
    logger.info("Deploying main router...")
    router_handle = serve.run(
        MainRouterDeployment.bind(
            algorunner_handle=algorunner_handle,
            screener_handle=screener_handle,
            tickscrawler_handle=tickscrawler_handle
        ),
        name="main-router",
        route_prefix="/"
    )
    logger.info("✅ Main router deployed")
    
    logger.info("All services deployed successfully!")
    logger.info("📍 Service endpoints:")
    logger.info("   • Main API: http://localhost:8000")
    logger.info("   • Health check: http://localhost:8000/health")
    logger.info("   • Algorunner: http://localhost:8000/api/algorunner/")
    logger.info("   • Screener: http://localhost:8000/api/screener/")
    logger.info("   • Tickscrawler: http://localhost:8000/api/tickscrawler/")
    
    return {
        "router": router_handle,
        "algorunner": algorunner_handle,
        "screener": screener_handle,
        "tickscrawler": tickscrawler_handle
    }

if __name__ == "__main__":
    try:
        deploy_services()
        logger.info("Deployment completed successfully!")
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        sys.exit(1)
