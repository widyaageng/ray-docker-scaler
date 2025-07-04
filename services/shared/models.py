"""
Shared Data Models

This module contains data models and schemas used across all services.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from enum import Enum


class ServiceStatus(Enum):
    """Enumeration for service status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class DataType(Enum):
    """Enumeration for data types."""
    TICK = "tick"
    OHLC = "ohlc"
    TRADE = "trade"
    QUOTE = "quote"
    NEWS = "news"
    FUNDAMENTAL = "fundamental"


@dataclass
class TickData:
    """Data model for tick data."""
    symbol: str
    timestamp: datetime
    price: float
    volume: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    source: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "price": self.price,
            "volume": self.volume,
            "bid": self.bid,
            "ask": self.ask,
            "source": self.source
        }


@dataclass
class OHLCData:
    """Data model for OHLC (Open, High, Low, Close) data."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    source: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "source": self.source
        }


@dataclass
class ServiceHealthcheck:
    """Data model for service health check."""
    service_name: str
    status: ServiceStatus
    uptime: float
    last_check: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "service_name": self.service_name,
            "status": self.status.value,
            "uptime": self.uptime,
            "last_check": self.last_check.isoformat(),
            "details": self.details
        }


@dataclass
class AlgorithmConfig:
    """Data model for algorithm configuration."""
    algorithm_id: str
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "algorithm_id": self.algorithm_id,
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class AlgorithmExecution:
    """Data model for algorithm execution."""
    execution_id: str
    algorithm_id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "execution_id": self.execution_id,
            "algorithm_id": self.algorithm_id,
            "status": self.status,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "parameters": self.parameters,
            "result": self.result,
            "error": self.error
        }


@dataclass
class ScreeningFilter:
    """Data model for screening filter."""
    filter_id: str
    name: str
    description: str
    filter_type: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "filter_id": self.filter_id,
            "name": self.name,
            "description": self.description,
            "filter_type": self.filter_type,
            "parameters": self.parameters,
            "enabled": self.enabled,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class DataSource:
    """Data model for data source configuration."""
    source_id: str
    name: str
    source_type: str
    description: str
    endpoints: Dict[str, str] = field(default_factory=dict)
    supported_symbols: List[str] = field(default_factory=list)
    enabled: bool = True
    rate_limit: Optional[int] = None
    api_key: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source_id": self.source_id,
            "name": self.name,
            "source_type": self.source_type,
            "description": self.description,
            "endpoints": self.endpoints,
            "supported_symbols": self.supported_symbols,
            "enabled": self.enabled,
            "rate_limit": self.rate_limit,
            "api_key": "***" if self.api_key else None  # Mask API key
        }


@dataclass
class StreamConfig:
    """Data model for streaming configuration."""
    stream_id: str
    source_id: str
    symbols: List[str]
    data_type: DataType
    status: str = "inactive"
    created_at: datetime = field(default_factory=datetime.now)
    last_message_at: Optional[datetime] = None
    message_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stream_id": self.stream_id,
            "source_id": self.source_id,
            "symbols": self.symbols,
            "data_type": self.data_type.value,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "message_count": self.message_count
        }


@dataclass
class APIResponse:
    """Standard API response model."""
    status: str
    timestamp: datetime = field(default_factory=datetime.now)
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
        
        if self.data is not None:
            result["data"] = self.data
        if self.error is not None:
            result["error"] = self.error
            
        return result


@dataclass
class MarketData:
    """Generic market data model."""
    symbol: str
    timestamp: datetime
    data_type: DataType
    data: Dict[str, Any]
    source: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "data_type": self.data_type.value,
            "data": self.data,
            "source": self.source
        }


@dataclass
class ServiceMetrics:
    """Data model for service metrics."""
    service_name: str
    timestamp: datetime
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    request_count: Optional[int] = None
    error_count: Optional[int] = None
    avg_response_time: Optional[float] = None
    active_connections: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "service_name": self.service_name,
            "timestamp": self.timestamp.isoformat(),
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "avg_response_time": self.avg_response_time,
            "active_connections": self.active_connections
        }


# Type aliases for common data structures
RequestData = Dict[str, Any]
ResponseData = Dict[str, Any]
ConfigData = Dict[str, Any]
MetricsData = Dict[str, Any]
