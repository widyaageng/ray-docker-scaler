"""
Configuration for the Tickscrawler Service
"""

import os
from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class TickscrawlerServiceConfig:
    """Configuration for the tickscrawler service."""
    
    name: str = "tickscrawler"
    num_replicas: int = 2
    max_ongoing_requests: int = 100
    ray_actor_options: Dict[str, Any] = None  # type: ignore
    
    # Crawling settings
    max_concurrent_crawls: int = 10
    default_crawl_limit: int = 1000
    crawl_timeout: int = 300  # seconds

    # Autoscaling settings
    min_replicas: int = 1
    max_replicas: int = 10
    target_num_ongoing_requests_per_replica: int = 100
    scale_up_delay_s: int = 10
    scale_down_delay_s: int = 60
    
    # Streaming settings
    max_active_streams: int = 20
    stream_buffer_size: int = 1000
    
    # Rate limiting
    requests_per_minute: int = 100
    
    # Data sources
    data_sources: Dict[str, Dict[str, Any]] = None  # type: ignore
    
    def __post_init__(self):
        if self.ray_actor_options is None:
            self.ray_actor_options = {
                "num_cpus": 0.2,  # Reduced from 0.5 to 0.2
                "memory": 64 * 1024 * 1024  # Reduced from 128MB to 64MB
            }
        
        if self.data_sources is None:
            self.data_sources = {
                "binance": {
                    "api_key": os.getenv("BINANCE_API_KEY", ""),
                    "api_secret": os.getenv("BINANCE_API_SECRET", ""),
                    "enabled": os.getenv("BINANCE_ENABLED", "true").lower() == "true"
                },
                "alpha_vantage": {
                    "api_key": os.getenv("ALPHA_VANTAGE_API_KEY", ""),
                    "enabled": os.getenv("ALPHA_VANTAGE_ENABLED", "true").lower() == "true"
                },
                "yahoo_finance": {
                    "enabled": os.getenv("YAHOO_FINANCE_ENABLED", "true").lower() == "true"
                },
                "forex_api": {
                    "api_key": os.getenv("FOREX_API_KEY", ""),
                    "enabled": os.getenv("FOREX_API_ENABLED", "true").lower() == "true"
                }
            }


# Create service configuration instance
TICKSCRAWLER_SERVICE_CONFIG = TickscrawlerServiceConfig(
    num_replicas=int(os.getenv("TICKSCRAWLER_REPLICAS", "1")),  # Reduced from 3 to 1
    max_ongoing_requests=int(os.getenv("TICKSCRAWLER_MAX_ONGOING_REQUESTS", "100")),
    max_concurrent_crawls=int(os.getenv("TICKSCRAWLER_MAX_CRAWLS", "10")),
    default_crawl_limit=int(os.getenv("TICKSCRAWLER_DEFAULT_LIMIT", "1000")),
    crawl_timeout=int(os.getenv("TICKSCRAWLER_TIMEOUT", "300")),
    max_active_streams=int(os.getenv("TICKSCRAWLER_MAX_STREAMS", "20")),
    requests_per_minute=int(os.getenv("TICKSCRAWLER_RATE_LIMIT", "100")),
    min_replicas=int(os.getenv("TICKSCRAWLER_MIN_REPLICAS", "2")),
    max_replicas=int(os.getenv("TICKSCRAWLER_MAX_REPLICAS", "10")),
    target_num_ongoing_requests_per_replica=int(os.getenv("TICKSCRAWLER_TARGET_NUM_ONGOING_REQUESTS", "100")),
    scale_up_delay_s=int(os.getenv("TICKSCRAWLER_SCALE_UP_DELAY", "10")),
    scale_down_delay_s=int(os.getenv("TICKSCRAWLER_SCALE_DOWN_DELAY", "60"))
)
