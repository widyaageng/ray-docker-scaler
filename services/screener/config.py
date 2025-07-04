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
    max_concurrent_queries: int = 15
    ray_actor_options: Dict[str, Any] = None  # type: ignore
    
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
    max_concurrent_queries=int(os.getenv("SCREENER_MAX_QUERIES", "15")),
    data_refresh_interval=int(os.getenv("SCREENER_REFRESH_INTERVAL", "60")),
    max_results_per_query=int(os.getenv("SCREENER_MAX_RESULTS", "1000"))
)
