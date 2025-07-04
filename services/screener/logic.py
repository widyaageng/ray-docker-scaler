"""
Screener Business Logic

This module contains the core business logic for the screener service.
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List
import logging
import random

logger = logging.getLogger(__name__)


class ScreenerLogic:
    """
    Core business logic for the screener service.
    
    This class handles data screening, filtering, and market analysis.
    """
    
    def __init__(self):
        """Initialize the screener logic."""
        self.custom_filters: Dict[str, Dict[str, Any]] = {}
        self.available_filters = [
            {
                "id": "volume_filter",
                "name": "Volume Filter",
                "description": "Filter stocks by trading volume",
                "parameters": ["min_volume", "max_volume"]
            },
            {
                "id": "price_filter",
                "name": "Price Filter", 
                "description": "Filter stocks by price range",
                "parameters": ["min_price", "max_price"]
            },
            {
                "id": "market_cap_filter",
                "name": "Market Cap Filter",
                "description": "Filter stocks by market capitalization",
                "parameters": ["min_market_cap", "max_market_cap"]
            },
            {
                "id": "pe_ratio_filter",
                "name": "P/E Ratio Filter",
                "description": "Filter stocks by price-to-earnings ratio",
                "parameters": ["min_pe", "max_pe"]
            },
            {
                "id": "dividend_yield_filter",
                "name": "Dividend Yield Filter",
                "description": "Filter stocks by dividend yield",
                "parameters": ["min_yield", "max_yield"]
            }
        ]
        
        # Sample market data for demonstration
        self.sample_stocks = self._generate_sample_data()
        logger.info("Screener logic initialized")
    
    def _generate_sample_data(self) -> List[Dict[str, Any]]:
        """Generate sample stock data for demonstration."""
        stocks = []
        symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NVDA", "AMD", "INTC", "CRM"]
        
        for symbol in symbols:
            stock = {
                "symbol": symbol,
                "price": round(random.uniform(50, 300), 2),
                "volume": random.randint(1000000, 50000000),
                "market_cap": random.randint(10000000000, 3000000000000),  # 10B to 3T
                "pe_ratio": round(random.uniform(10, 40), 2),
                "dividend_yield": round(random.uniform(0, 5), 2),
                "sector": random.choice(["Technology", "Healthcare", "Finance", "Consumer", "Energy"]),
                "last_updated": datetime.now().isoformat()
            }
            stocks.append(stock)
        
        return stocks
    
    async def screen_data(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Screen stocks based on provided criteria.
        
        Args:
            request_data: Dictionary containing screening criteria
            
        Returns:
            Dictionary containing screening results
        """
        filters = request_data.get("filters", [])
        limit = request_data.get("limit", 100)
        
        # Simulate data processing time
        await asyncio.sleep(0.5)
        
        # Apply filters to sample data
        filtered_stocks = self.sample_stocks.copy()
        
        for filter_criteria in filters:
            filter_type = filter_criteria.get("type")
            parameters = filter_criteria.get("parameters", {})
            
            filtered_stocks = self._apply_filter(filtered_stocks, filter_type, parameters)
        
        # Limit results
        filtered_stocks = filtered_stocks[:limit]
        
        return {
            "total_stocks": len(self.sample_stocks),
            "filtered_count": len(filtered_stocks),
            "stocks": filtered_stocks,
            "filters_applied": len(filters),
            "scan_time": "0.5s"
        }
    
    def _apply_filter(
        self, 
        stocks: List[Dict[str, Any]], 
        filter_type: str, 
        parameters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Apply a specific filter to the stock list.
        
        Args:
            stocks: List of stocks to filter
            filter_type: Type of filter to apply
            parameters: Filter parameters
            
        Returns:
            Filtered list of stocks
        """
        if filter_type == "volume_filter":
            min_vol = parameters.get("min_volume", 0)
            max_vol = parameters.get("max_volume", float('inf'))
            return [s for s in stocks if min_vol <= s["volume"] <= max_vol]
        
        elif filter_type == "price_filter":
            min_price = parameters.get("min_price", 0)
            max_price = parameters.get("max_price", float('inf'))
            return [s for s in stocks if min_price <= s["price"] <= max_price]
        
        elif filter_type == "market_cap_filter":
            min_cap = parameters.get("min_market_cap", 0)
            max_cap = parameters.get("max_market_cap", float('inf'))
            return [s for s in stocks if min_cap <= s["market_cap"] <= max_cap]
        
        elif filter_type == "pe_ratio_filter":
            min_pe = parameters.get("min_pe", 0)
            max_pe = parameters.get("max_pe", float('inf'))
            return [s for s in stocks if min_pe <= s["pe_ratio"] <= max_pe]
        
        elif filter_type == "dividend_yield_filter":
            min_yield = parameters.get("min_yield", 0)
            max_yield = parameters.get("max_yield", float('inf'))
            return [s for s in stocks if min_yield <= s["dividend_yield"] <= max_yield]
        
        else:
            # Unknown filter type, return unfiltered
            return stocks
    
    def get_available_filters(self) -> List[Dict[str, Any]]:
        """
        Get list of available screening filters.
        
        Returns:
            List of available filters
        """
        all_filters = self.available_filters.copy()
        
        # Add custom filters
        for filter_id, filter_data in self.custom_filters.items():
            all_filters.append({
                "id": filter_id,
                "name": filter_data["name"],
                "description": filter_data["description"],
                "parameters": filter_data["parameters"],
                "custom": True
            })
        
        return all_filters
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get the current status of the screener service.
        
        Returns:
            Dictionary containing service status
        """
        return {
            "service": "screener",
            "status": "healthy",
            "available_filters": len(self.available_filters),
            "custom_filters": len(self.custom_filters),
            "data_sources": ["sample_data"],  # In real implementation, list actual data sources
            "total_stocks": len(self.sample_stocks),
            "uptime": "operational"
        }
    
    async def create_custom_filter(self, filter_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a custom screening filter.
        
        Args:
            filter_data: Dictionary containing filter definition
            
        Returns:
            Dictionary containing creation result
        """
        filter_id = filter_data.get("id") or str(uuid.uuid4())
        name = filter_data.get("name")
        description = filter_data.get("description")
        parameters = filter_data.get("parameters", [])
        
        if not name:
            raise ValueError("Filter name is required")
        
        # Store custom filter
        self.custom_filters[filter_id] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "created_at": datetime.now().isoformat()
        }
        
        return {
            "filter_id": filter_id,
            "name": name,
            "message": "Custom filter created successfully"
        }
    
    async def get_market_overview(self) -> Dict[str, Any]:
        """
        Get market overview data.
        
        Returns:
            Dictionary containing market overview
        """
        # Simulate data processing
        await asyncio.sleep(0.3)
        
        # Calculate overview statistics from sample data
        total_stocks = len(self.sample_stocks)
        avg_price = sum(s["price"] for s in self.sample_stocks) / total_stocks
        total_volume = sum(s["volume"] for s in self.sample_stocks)
        
        sectors = {}
        for stock in self.sample_stocks:
            sector = stock["sector"]
            if sector not in sectors:
                sectors[sector] = {"count": 0, "total_market_cap": 0}
            sectors[sector]["count"] += 1
            sectors[sector]["total_market_cap"] += stock["market_cap"]
        
        return {
            "total_stocks": total_stocks,
            "average_price": round(avg_price, 2),
            "total_volume": total_volume,
            "sectors": sectors,
            "market_cap_range": {
                "min": min(s["market_cap"] for s in self.sample_stocks),
                "max": max(s["market_cap"] for s in self.sample_stocks)
            },
            "price_range": {
                "min": min(s["price"] for s in self.sample_stocks),
                "max": max(s["price"] for s in self.sample_stocks)
            },
            "last_updated": datetime.now().isoformat()
        }
