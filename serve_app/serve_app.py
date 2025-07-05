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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Handle both internal and external imports
try:
    from .router_deployment import MainRouterDeployment
except ImportError:
    # When running inside cluster, add workspace to path
    if '/workspace' not in sys.path:
        sys.path.insert(0, '/workspace')
        logger.info("Added '/workspace' to sys.path for internal imports")
    from serve_app.router_deployment import MainRouterDeployment

from services.algorunner.deployment import AlgorunnerDeployment
from services.screener.deployment import ScreenerDeployment
from services.tickscrawler.deployment import TickscrawlerDeployment


def deploy_services(
        address: str = "auto",
        serve_host: str = "0.0.0.0",
        serve_port: int = 8000
        ) -> Dict[str, Any]:
    """
    Deploy all Ray Serve services and return deployment handles.

    Args:
        address: Ray cluster address (default is "auto" for internal deployment)
        serve_host: Host for Ray Serve (default is "0.0.0.0")
        serve_port: Port for Ray Serve (default is 8000)

    Returns:
        Dict containing deployment handles for all services
    """
    logger.info("Starting Ray Serve application deployment...")
    
    # Connect to Ray cluster (use auto for internal deployment)
    if not ray.is_initialized():
        logger.info(f"Connecting to Ray cluster at {address}...")
        ray.init(address=address, ignore_reinit_error=True)

    # Start Ray Serve
    logger.info(f"Starting Ray Serve at {serve_host}:{serve_port}...")
    serve.start(
        detached=True,
        proxy_location="EveryNode",
        http_options={"host": serve_host, "port": serve_port}
    )
    logger.info("Ray Serve started successfully")
    
    # Deploy individual services (without HTTP routes)
    algorunner_handle = None
    screener_handle = None
    tickscrawler_handle = None
    router_handle = None

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
        blocking=False,
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


def shutdown_services(
        address: str = "auto",
):
    """
    Shutdown all Ray Serve services and Ray cluster.
    Args:
        address: Ray cluster address (default is "auto" for internal deployment)
    """
    logger.info("Shutting down Ray Serve services...")
    
    try:
        # Connect to Ray if not already connected
        if not ray.is_initialized():
            logger.info("Connecting to Ray cluster for shutdown...")
            ray.init(address=address, ignore_reinit_error=True)
        
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

    parser.add_argument(
        "--address", 
        type=str, 
        default="auto",
        help="Ray cluster address (default is 'auto' for internal deployment)"
    )

    parser.add_argument(
        "--serve-host", 
        type=str, 
        default="0.0.0.0",
        help="Host for Ray Serve (default is '0.0.0.0')"
    )

    parser.add_argument(
        "--serve-port", 
        type=int, 
        default=8000,
        help="Port for Ray Serve (default is 8000)"
    )

    args = parser.parse_args()
    
    if args.action == "shutdown":
        shutdown_services(
            address=args.address
        )
        return
    
    # Default action is deploy
    try:
        _ = deploy_services(
            address=args.address,
            serve_host=args.serve_host,
            serve_port=args.serve_port
        )
        logger.info("Ray Serve application is running. Press Ctrl+C to stop.")
        
    #     # Keep the application running
    #     import time
    #     while True:
    #         time.sleep(1)
            
    # except KeyboardInterrupt:
    #     logger.info("Shutting down Ray Serve application...")
    #     shutdown_services(
    #         address=args.address
    #     )
    except Exception as e:
        logger.error(f"Error in Ray Serve application: {e}")
        shutdown_services(
            address=args.address
        )
        raise


if __name__ == "__main__":
    main()
