"""
Configuration settings for the Ray Serve application.
"""

import os
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class AppConfig:
    """Main application configuration."""
    
    # Ray Serve settings
    serve_host: str = "0.0.0.0"
    serve_port: int = 8000
    
    # Service settings
    max_concurrent_queries: int = 100
    
    # Logging
    log_level: str = "INFO"
    
    # Environment
    environment: str = "development"
    
    @classmethod
    def from_env(cls) -> "AppConfig":
        """Create configuration from environment variables."""
        return cls(
            serve_host=os.getenv("SERVE_HOST", "0.0.0.0"),
            serve_port=int(os.getenv("SERVE_PORT", "8000")),
            max_concurrent_queries=int(os.getenv("MAX_CONCURRENT_QUERIES", "100")),
            log_level=os.getenv("LOG_LEVEL", "INFO") if cls.environment != "development" else "development",
            environment=os.getenv("ENVIRONMENT", "development")
        )


@dataclass
class ServiceConfig:
    """Base configuration for individual services."""
    
    name: str
    max_concurrent_queries: int = 10
    num_replicas: int = 1
    ray_actor_options: Dict[str, Any] = None  # type: ignore
    
    def __post_init__(self):
        if self.ray_actor_options is None:
            self.ray_actor_options = {}


# # Service-specific configurations
# ALGORUNNER_CONFIG = ServiceConfig(
#     name="algorunner",
#     max_concurrent_queries=int(os.getenv("ALGORUNNER_MAX_QUERIES", "20")),
#     num_replicas=int(os.getenv("ALGORUNNER_REPLICAS", "2")),
# )

# SCREENER_CONFIG = ServiceConfig(
#     name="screener",
#     max_concurrent_queries=int(os.getenv("SCREENER_MAX_QUERIES", "15")),
#     num_replicas=int(os.getenv("SCREENER_REPLICAS", "1")),
# )

# TICKSCRAWLER_CONFIG = ServiceConfig(
#     name="tickscrawler",
#     max_concurrent_queries=int(os.getenv("TICKSCRAWLER_MAX_QUERIES", "30")),
#     num_replicas=int(os.getenv("TICKSCRAWLER_REPLICAS", "3")),
# )
