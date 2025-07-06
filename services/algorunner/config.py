"""
Configuration for the Algorunner Service
"""

import os
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class AlgorunnerServiceConfig:
    """Configuration for the algorunner service."""
    
    name: str = "algorunner"
    num_replicas: int = 2
    max_ongoing_requests: int = 100
    ray_actor_options: Dict[str, Any] = None  # type: ignore
    
    # Algorithm execution settings
    max_execution_time: int = 300  # seconds
    max_concurrent_algorithms: int = 10

    # Autoscaling settings
    min_replicas: int = 1
    max_replicas: int = 10
    target_num_ongoing_requests_per_replica: int = 100
    scale_up_delay_s: int = 10
    scale_down_delay_s: int = 60
    
    # Data sources
    data_sources: Dict[str, str] = None  # type: ignore
    
    def __post_init__(self):
        if self.ray_actor_options is None:
            self.ray_actor_options = {
                "num_cpus": 0.2,  # Reduced from 0.5 to 0.2
                "memory": 64 * 1024 * 1024  # Reduced from 128MB to 64MB
            }
        
        if self.data_sources is None:
            self.data_sources = {
                "market_data": os.getenv("MARKET_DATA_URL", "ws://localhost:8080"),
                "historical_data": os.getenv("HISTORICAL_DATA_URL", "http://localhost:8081")
            }


# Create service configuration instance
ALGORUNNER_SERVICE_CONFIG = AlgorunnerServiceConfig(
    num_replicas=int(os.getenv("ALGORUNNER_REPLICAS", "1")),  # Reduced from 2 to 1
    max_ongoing_requests=int(os.getenv("ALGORUNNER_MAX_ONGOING_REQUESTS", "100")),
    max_execution_time=int(os.getenv("ALGORUNNER_MAX_EXECUTION_TIME", "300")),
    max_concurrent_algorithms=int(os.getenv("ALGORUNNER_MAX_CONCURRENT", "10")),
    min_replicas=int(os.getenv("ALGORUNNER_MIN_REPLICAS", "2")),
    max_replicas=int(os.getenv("ALGORUNNER_MAX_REPLICAS", "10")),
    target_num_ongoing_requests_per_replica=int(os.getenv("ALGORUNNER_TARGET_NUM_ONGOING_REQUESTS", "100")),
    scale_up_delay_s=int(os.getenv("ALGORUNNER_SCALE_UP_DELAY", "10")),
    scale_down_delay_s=int(os.getenv("ALGORUNNER_SCALE_DOWN_DELAY", "60"))
)
