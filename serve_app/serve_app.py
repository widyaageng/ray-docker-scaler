"""
Ray Serve Application Entry Point

This module serves as the main entry point for Ray Serve deployments.
It initializes and deploys all the microservices.
"""

import ray
from ray import serve
import logging
import sys
import os
from typing import Dict, Any

# Handle both internal and external imports
try:
    from .router_deployment import MainRouterDeployment
except ImportError:
    # When running inside cluster, add workspace to path
    if '/workspace' not in sys.path:
        sys.path.insert(0, '/workspace')
    from serve_app.router_deployment import MainRouterDeployment

from services.algorunner.deployment import AlgorunnerDeployment
from services.screener.deployment import ScreenerDeployment
from services.tickscrawler.deployment import TickscrawlerDeployment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def deploy_services() -> Dict[str, Any]:
    """
    Deploy all Ray Serve services and return deployment handles.
    
    Returns:
        Dict containing deployment handles for all services
    """
    logger.info("Starting Ray Serve application deployment...")
    
    # Connect to Ray cluster (use auto for internal deployment)
    if not ray.is_initialized():
        logger.info("Connecting to Ray cluster...")
        ray.init(address="auto", ignore_reinit_error=True)
    
    # Start Ray Serve
    logger.info("Starting Ray Serve...")
    serve.start(detached=True, http_options={"host": "0.0.0.0", "port": 8000})
    logger.info("Ray Serve started successfully")
    
    # Deploy individual services (without HTTP routes)
    logger.info("Deploying individual services...")
    algorunner_handle = serve.run(AlgorunnerDeployment.bind(), name="algorunner", route_prefix=None)
    logger.info("Algorunner service deployed")
    
    screener_handle = serve.run(ScreenerDeployment.bind(), name="screener", route_prefix=None)
    logger.info("Screener service deployed")
    
    tickscrawler_handle = serve.run(TickscrawlerDeployment.bind(), name="tickscrawler", route_prefix=None)
    logger.info("Tickscrawler service deployed")
    
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
    logger.info("Main router deployed")
    
    deployments = {
        "router": router_handle,
        "algorunner": algorunner_handle,
        "screener": screener_handle,
        "tickscrawler": tickscrawler_handle
    }
    
    logger.info("All services deployed successfully")
    return deployments


def shutdown_services():
    """
    Shutdown all Ray Serve services and Ray cluster.
    """
    logger.info("Shutting down Ray Serve services...")
    
    try:
        # Connect to Ray if not already connected
        if not ray.is_initialized():
            logger.info("Connecting to Ray cluster for shutdown...")
            ray.init(address="auto", ignore_reinit_error=True)
        
        # Shutdown Ray Serve
        logger.info("Shutting down Ray Serve...")
        serve.shutdown()
        logger.info("Ray Serve shut down successfully")
        
        # Shutdown Ray
        logger.info("Shutting down Ray cluster connection...")
        ray.shutdown()
        logger.info("Ray cluster connection shut down successfully")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
        raise


def main():
    """Main entry point for the Ray Serve application."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Ray Serve Application Manager")
    parser.add_argument(
        "action", 
        choices=["deploy", "shutdown"], 
        nargs="?", 
        default="deploy",
        help="Action to perform: deploy services or shutdown"
    )
    
    args = parser.parse_args()
    
    if args.action == "shutdown":
        shutdown_services()
        return
    
    # Default action is deploy
    try:
        deployments = deploy_services()
        logger.info("Ray Serve application is running. Press Ctrl+C to stop.")
        
        # Keep the application running
        import time
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Shutting down Ray Serve application...")
        shutdown_services()
    except Exception as e:
        logger.error(f"Error in Ray Serve application: {e}")
        shutdown_services()
        raise


if __name__ == "__main__":
    main()
