"""
Tickscrawler Business Logic

This module contains the core business logic for the tickscrawler service.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging
import random

logger = logging.getLogger(__name__)


class TickscrawlerLogic:
    """
    Core business logic for the tickscrawler service.
    
    This class handles data crawling, streaming, and historical data retrieval.
    """
    
    def __init__(self):
        """Initialize the tickscrawler logic."""
        self.active_streams: Dict[str, Dict[str, Any]] = {}
        self.crawl_history: List[Dict[str, Any]] = []
        
        self.available_sources = [
            {
                "id": "binance",
                "name": "Binance",
                "type": "cryptocurrency",
                "description": "Binance cryptocurrency exchange",
                "endpoints": {
                    "websocket": "wss://stream.binance.com:9443",
                    "rest": "https://api.binance.com"
                },
                "supported_symbols": ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT"]
            },
            {
                "id": "alpha_vantage",
                "name": "Alpha Vantage",
                "type": "stocks",
                "description": "Stock market data provider",
                "endpoints": {
                    "rest": "https://www.alphavantage.co/query"
                },
                "supported_symbols": ["AAPL", "GOOGL", "MSFT", "AMZN"]
            },
            {
                "id": "yahoo_finance",
                "name": "Yahoo Finance",
                "type": "stocks",
                "description": "Yahoo Finance data source",
                "endpoints": {
                    "rest": "https://query1.finance.yahoo.com"
                },
                "supported_symbols": ["^GSPC", "^IXIC", "^DJI"]
            },
            {
                "id": "forex_api",
                "name": "Forex API",
                "type": "forex",
                "description": "Foreign exchange rates",
                "endpoints": {
                    "rest": "https://api.forex.com"
                },
                "supported_symbols": ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
            }
        ]
        
        logger.info("Tickscrawler logic initialized")
    
    async def crawl_data(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Crawl market data based on provided parameters.
        
        Args:
            request_data: Dictionary containing crawling parameters
            
        Returns:
            Dictionary containing crawled data results
        """
        source_id = request_data.get("source_id")
        symbols = request_data.get("symbols", [])
        data_type = request_data.get("data_type", "ticks")
        limit = request_data.get("limit", 100)
        
        if not source_id:
            raise ValueError("source_id is required")
        
        if not symbols:
            raise ValueError("symbols list is required")
        
        # Find source
        source = next((s for s in self.available_sources if s["id"] == source_id), None)
        if not source:
            raise ValueError(f"Source {source_id} not found")
        
        # Generate crawl ID
        crawl_id = str(uuid.uuid4())
        
        # Store crawl info
        crawl_info = {
            "crawl_id": crawl_id,
            "source_id": source_id,
            "symbols": symbols,
            "data_type": data_type,
            "limit": limit,
            "start_time": datetime.now().isoformat(),
            "status": "running"
        }
        
        self.crawl_history.append(crawl_info)
        
        try:
            # Simulate data crawling
            crawled_data = await self._simulate_data_crawling(source, symbols, data_type, limit)
            
            crawl_info["status"] = "completed"
            crawl_info["end_time"] = datetime.now().isoformat()
            crawl_info["records_count"] = len(crawled_data)
            
            return {
                "crawl_id": crawl_id,
                "source": source["name"],
                "data": crawled_data,
                "total_records": len(crawled_data),
                "symbols": symbols,
                "data_type": data_type
            }
            
        except Exception as e:
            crawl_info["status"] = "failed"
            crawl_info["error"] = str(e)
            crawl_info["end_time"] = datetime.now().isoformat()
            raise e
    
    async def _simulate_data_crawling(
        self, 
        source: Dict[str, Any], 
        symbols: List[str], 
        data_type: str, 
        limit: int
    ) -> List[Dict[str, Any]]:
        """
        Simulate data crawling (replace with actual crawling logic).
        
        Args:
            source: Data source configuration
            symbols: List of symbols to crawl
            data_type: Type of data to crawl
            limit: Maximum number of records
            
        Returns:
            List of crawled data records
        """
        # Simulate crawling time
        await asyncio.sleep(1.5)
        
        crawled_data = []
        
        for symbol in symbols:
            for i in range(min(limit // len(symbols), 50)):  # Max 50 per symbol
                if data_type == "ticks":
                    record = {
                        "symbol": symbol,
                        "timestamp": (datetime.now() - timedelta(seconds=i*10)).isoformat(),
                        "price": round(random.uniform(100, 1000), 4),
                        "volume": random.randint(100, 10000),
                        "bid": round(random.uniform(99, 999), 4),
                        "ask": round(random.uniform(101, 1001), 4),
                        "source": source["id"]
                    }
                elif data_type == "ohlc":
                    base_price = random.uniform(100, 1000)
                    record = {
                        "symbol": symbol,
                        "timestamp": (datetime.now() - timedelta(minutes=i)).isoformat(),
                        "open": round(base_price, 4),
                        "high": round(base_price * random.uniform(1.0, 1.05), 4),
                        "low": round(base_price * random.uniform(0.95, 1.0), 4),
                        "close": round(base_price * random.uniform(0.98, 1.02), 4),
                        "volume": random.randint(1000, 100000),
                        "source": source["id"]
                    }
                else:
                    record = {
                        "symbol": symbol,
                        "timestamp": datetime.now().isoformat(),
                        "data": f"Sample {data_type} data for {symbol}",
                        "source": source["id"]
                    }
                
                crawled_data.append(record)
        
        return crawled_data
    
    def get_available_sources(self) -> List[Dict[str, Any]]:
        """
        Get list of available data sources.
        
        Returns:
            List of available data sources
        """
        return self.available_sources.copy()
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get the current status of the tickscrawler service.
        
        Returns:
            Dictionary containing service status
        """
        return {
            "service": "tickscrawler",
            "status": "healthy",
            "available_sources": len(self.available_sources),
            "active_streams": len(self.active_streams),
            "total_crawls": len(self.crawl_history),
            "uptime": "operational"
        }
    
    async def start_streaming(self, stream_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Start streaming data from a source.
        
        Args:
            stream_config: Dictionary containing streaming configuration
            
        Returns:
            Dictionary containing streaming setup result
        """
        source_id = stream_config.get("source_id")
        symbols = stream_config.get("symbols", [])
        
        if not source_id:
            raise ValueError("source_id is required")
        
        # Find source
        source = next((s for s in self.available_sources if s["id"] == source_id), None)
        if not source:
            raise ValueError(f"Source {source_id} not found")
        
        # Generate stream ID
        stream_id = str(uuid.uuid4())
        
        # Store stream info
        stream_info = {
            "stream_id": stream_id,
            "source_id": source_id,
            "symbols": symbols,
            "start_time": datetime.now().isoformat(),
            "status": "active",
            "messages_received": 0
        }
        
        self.active_streams[stream_id] = stream_info
        
        # Simulate stream setup
        await asyncio.sleep(0.5)
        
        return {
            "stream_id": stream_id,
            "source": source["name"],
            "symbols": symbols,
            "status": "started",
            "websocket_url": source["endpoints"].get("websocket", "N/A")
        }
    
    async def stop_streaming(self, stream_id: str) -> Dict[str, Any]:
        """
        Stop a streaming connection.
        
        Args:
            stream_id: ID of the stream to stop
            
        Returns:
            Dictionary containing stop operation result
        """
        if stream_id not in self.active_streams:
            raise ValueError(f"Stream {stream_id} not found or not active")
        
        stream_info = self.active_streams[stream_id]
        stream_info["status"] = "stopped"
        stream_info["end_time"] = datetime.now().isoformat()
        
        # Remove from active streams
        del self.active_streams[stream_id]
        
        return {
            "stream_id": stream_id,
            "status": "stopped",
            "duration": "active for some time",
            "messages_received": stream_info["messages_received"]
        }
    
    async def get_historical_data(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get historical data from a source.
        
        Args:
            request_data: Dictionary containing historical data request
            
        Returns:
            Dictionary containing historical data
        """
        source_id = request_data.get("source_id")
        symbol = request_data.get("symbol")
        start_date = request_data.get("start_date")
        end_date = request_data.get("end_date")
        interval = request_data.get("interval", "1m")
        
        if not all([source_id, symbol, start_date, end_date]):
            raise ValueError("source_id, symbol, start_date, and end_date are required")
        
        # Find source
        source = next((s for s in self.available_sources if s["id"] == source_id), None)
        if not source:
            raise ValueError(f"Source {source_id} not found")
        
        # Simulate historical data retrieval
        await asyncio.sleep(1.0)
        
        # Generate sample historical data
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00') if start_date else datetime.now().isoformat())
        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00') if end_date else datetime.now().isoformat())
        
        historical_data = []
        current_dt = start_dt
        base_price = random.uniform(100, 1000)
        
        while current_dt <= end_dt:
            # Generate OHLC data
            open_price = base_price
            high_price = open_price * random.uniform(1.0, 1.02)
            low_price = open_price * random.uniform(0.98, 1.0)
            close_price = open_price * random.uniform(0.99, 1.01)
            
            historical_data.append({
                "timestamp": current_dt.isoformat(),
                "symbol": symbol,
                "open": round(open_price, 4),
                "high": round(high_price, 4),
                "low": round(low_price, 4),
                "close": round(close_price, 4),
                "volume": random.randint(1000, 50000)
            })
            
            # Move to next interval
            if interval == "1m":
                current_dt += timedelta(minutes=1)
            elif interval == "5m":
                current_dt += timedelta(minutes=5)
            elif interval == "1h":
                current_dt += timedelta(hours=1)
            elif interval == "1d":
                current_dt += timedelta(days=1)
            else:
                current_dt += timedelta(minutes=1)
            
            base_price = close_price  # Use previous close as next base
            
            # Limit data points to prevent excessive generation
            if len(historical_data) >= 1000:
                break
        
        return {
            "symbol": symbol,
            "source": source["name"],
            "interval": interval,
            "start_date": start_date,
            "end_date": end_date,
            "data_points": len(historical_data),
            "data": historical_data
        }
