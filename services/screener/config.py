"""
Configuration for the Screener Service
"""

import os
from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class ScreenerServiceConfig:
    """Configuration for the screener service."""
    
    name: str = "screener"
    num_replicas: int = 1
    ray_actor_options: Dict[str, Any] = None  # type: ignore
    max_ongoing_requests: int = 100  # Maximum concurrent queries allowed

    # Autoscaling settings
    min_replicas: int = 1
    max_replicas: int = 10
    target_num_ongoing_requests_per_replica: int = 100
    scale_up_delay_s: int = 10
    scale_down_delay_s: int = 60
    
    # Data source settings
    data_refresh_interval: int = 60  # seconds
    max_results_per_query: int = 1000
    
    # Supported markets
    supported_markets: List[str] = None  # type: ignore
    
    # Data sources
    data_sources: Dict[str, str] = None  # type: ignore
    
    def __post_init__(self):
        if self.ray_actor_options is None:
            self.ray_actor_options = {
                "num_cpus": 0.2,  # Reduced from 0.5 to 0.2
                "memory": 64 * 1024 * 1024  # Reduced from 128MB to 64MB
            }
        
        if self.supported_markets is None:
            self.supported_markets = ["NYSE", "NASDAQ", "AMEX"]
        
        if self.data_sources is None:
            self.data_sources = {
                "market_data": os.getenv("MARKET_DATA_API", "https://api.marketdata.com"),
                "fundamental_data": os.getenv("FUNDAMENTAL_DATA_API", "https://api.fundamentals.com"),
                "news_data": os.getenv("NEWS_DATA_API", "https://api.news.com")
            }


# Create service configuration instance
SCREENER_SERVICE_CONFIG = ScreenerServiceConfig(
    num_replicas=int(os.getenv("SCREENER_REPLICAS", "1")),
    max_ongoing_requests=int(os.getenv("SCREENER_MAX_ONGOING_REQUESTS", "100")),
    data_refresh_interval=int(os.getenv("SCREENER_REFRESH_INTERVAL", "60")),
    max_results_per_query=int(os.getenv("SCREENER_MAX_RESULTS", "1000")),
    min_replicas=int(os.getenv("SCREENER_MIN_REPLICAS", "1")),
    max_replicas=int(os.getenv("SCREENER_MAX_REPLICAS", "10")),
    target_num_ongoing_requests_per_replica=int(os.getenv("SCREENER_TARGET_NUM_ONGOING_REQUESTS", "100")),
    scale_up_delay_s=int(os.getenv("SCREENER_SCALE_UP_DELAY", "10")),
    scale_down_delay_s=int(os.getenv("SCREENER_SCALE_DOWN_DELAY", "60"))
)
