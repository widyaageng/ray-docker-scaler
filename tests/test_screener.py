"""
Unit tests for the Screener service.
"""

import pytest # type: ignore
import asyncio
from unittest.mock import Mock, patch
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.screener.logic import ScreenerLogic
from services.screener.deployment import ScreenerDeployment


class TestScreenerLogic:
    """Test cases for ScreenerLogic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.logic = ScreenerLogic()
    
    def test_initialization(self):
        """Test logic initialization."""
        assert self.logic.custom_filters == {}
        assert len(self.logic.available_filters) > 0
        assert len(self.logic.sample_stocks) > 0
    
    def test_get_available_filters(self):
        """Test getting available filters."""
        filters = self.logic.get_available_filters()
        assert isinstance(filters, list)
        assert len(filters) > 0
        
        for filter_def in filters:
            assert "id" in filter_def
            assert "name" in filter_def
            assert "description" in filter_def
            assert "parameters" in filter_def
    
    @pytest.mark.asyncio
    async def test_screen_data_no_filters(self):
        """Test screening data with no filters."""
        request_data = {"filters": [], "limit": 10}
        
        result = await self.logic.screen_data(request_data)
        
        assert "total_stocks" in result
        assert "filtered_count" in result
        assert "stocks" in result
        assert len(result["stocks"]) <= 10
        assert result["filtered_count"] <= result["total_stocks"]
    
    @pytest.mark.asyncio
    async def test_screen_data_with_price_filter(self):
        """Test screening data with price filter."""
        request_data = {
            "filters": [
                {
                    "type": "price_filter",
                    "parameters": {"min_price": 100, "max_price": 200}
                }
            ],
            "limit": 50
        }
        
        result = await self.logic.screen_data(request_data)
        
        assert "stocks" in result
        
        # Check that all returned stocks are within the price range
        for stock in result["stocks"]:
            assert 100 <= stock["price"] <= 200
    
    @pytest.mark.asyncio
    async def test_screen_data_with_volume_filter(self):
        """Test screening data with volume filter."""
        request_data = {
            "filters": [
                {
                    "type": "volume_filter",
                    "parameters": {"min_volume": 5000000}
                }
            ]
        }
        
        result = await self.logic.screen_data(request_data)
        
        # Check that all returned stocks meet the volume requirement
        for stock in result["stocks"]:
            assert stock["volume"] >= 5000000
    
    @pytest.mark.asyncio
    async def test_screen_data_with_multiple_filters(self):
        """Test screening data with multiple filters."""
        request_data = {
            "filters": [
                {
                    "type": "price_filter",
                    "parameters": {"min_price": 100, "max_price": 250}
                },
                {
                    "type": "pe_ratio_filter",
                    "parameters": {"min_pe": 15, "max_pe": 30}
                }
            ]
        }
        
        result = await self.logic.screen_data(request_data)
        
        # Check that all returned stocks meet both criteria
        for stock in result["stocks"]:
            assert 100 <= stock["price"] <= 250
            assert 15 <= stock["pe_ratio"] <= 30
    
    def test_apply_filter_price(self):
        """Test price filter application."""
        stocks = [
            {"symbol": "A", "price": 50},
            {"symbol": "B", "price": 150},
            {"symbol": "C", "price": 250}
        ]
        
        filtered = self.logic._apply_filter(
            stocks, 
            "price_filter", 
            {"min_price": 100, "max_price": 200}
        )
        
        assert len(filtered) == 1
        assert filtered[0]["symbol"] == "B"
    
    def test_apply_filter_unknown_type(self):
        """Test unknown filter type."""
        stocks = [{"symbol": "A", "price": 100}]
        
        filtered = self.logic._apply_filter(
            stocks, 
            "unknown_filter", 
            {"param": "value"}
        )
        
        # Should return unfiltered list
        assert filtered == stocks
    
    def test_get_service_status(self):
        """Test getting service status."""
        status = self.logic.get_service_status()
        
        assert status["service"] == "screener"
        assert status["status"] == "healthy"
        assert "available_filters" in status
        assert "custom_filters" in status
        assert "total_stocks" in status
    
    @pytest.mark.asyncio
    async def test_create_custom_filter(self):
        """Test creating a custom filter."""
        filter_data = {
            "name": "Test Filter",
            "description": "A test filter",
            "parameters": ["test_param"]
        }
        
        result = await self.logic.create_custom_filter(filter_data)
        
        assert "filter_id" in result
        assert result["name"] == "Test Filter"
        assert "message" in result
        
        # Check that it was added to custom filters
        assert len(self.logic.custom_filters) == 1
        
        # Check that it appears in available filters
        available = self.logic.get_available_filters()
        custom_filter = next((f for f in available if f.get("custom")), None)
        assert custom_filter is not None
        assert custom_filter["name"] == "Test Filter"
    
    @pytest.mark.asyncio
    async def test_create_custom_filter_missing_name(self):
        """Test creating custom filter without name."""
        filter_data = {"description": "A test filter"}
        
        with pytest.raises(ValueError, match="Filter name is required"):
            await self.logic.create_custom_filter(filter_data)
    
    @pytest.mark.asyncio
    async def test_get_market_overview(self):
        """Test getting market overview."""
        overview = await self.logic.get_market_overview()
        
        assert "total_stocks" in overview
        assert "average_price" in overview
        assert "total_volume" in overview
        assert "sectors" in overview
        assert "market_cap_range" in overview
        assert "price_range" in overview
        assert "last_updated" in overview
        
        # Check market cap range
        assert "min" in overview["market_cap_range"]
        assert "max" in overview["market_cap_range"]
        
        # Check price range
        assert "min" in overview["price_range"]
        assert "max" in overview["price_range"]


class TestScreenerDeployment:
    """Test cases for ScreenerDeployment."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.deployment = ScreenerDeployment()
    
    def test_initialization(self):
        """Test deployment initialization."""
        assert hasattr(self.deployment, 'logic')
        assert isinstance(self.deployment.logic, ScreenerLogic)
    
    @pytest.mark.asyncio
    async def test_screen_success(self):
        """Test successful screening through deployment."""
        request_data = {
            "filters": [
                {"type": "price_filter", "parameters": {"min_price": 100}}
            ]
        }
        
        result = await self.deployment.screen(request_data) # type: ignore
        
        assert result["status"] == "success"
        assert "result" in result
        assert "stocks" in result["result"]
    
    @pytest.mark.asyncio
    async def test_get_filters(self):
        """Test getting filters through deployment."""
        result = await self.deployment.get_filters() # type: ignore
        
        assert result["status"] == "success"
        assert "filters" in result
        assert len(result["filters"]) > 0
    
    @pytest.mark.asyncio
    async def test_get_status(self):
        """Test getting deployment status."""
        result = await self.deployment.get_status() # type: ignore
        
        assert result["status"] == "success"
        assert "data" in result
        assert result["data"]["service"] == "screener"
    
    @pytest.mark.asyncio
    async def test_create_custom_filter(self):
        """Test creating custom filter through deployment."""
        filter_data = {
            "name": "Test Filter",
            "description": "A test filter"
        }
        
        result = await self.deployment.create_custom_filter(filter_data) # type: ignore
        
        assert result["status"] == "success"
        assert "result" in result
    
    @pytest.mark.asyncio
    async def test_get_market_overview(self):
        """Test getting market overview through deployment."""
        result = await self.deployment.get_market_overview() # type: ignore
        
        assert result["status"] == "success"
        assert "overview" in result


if __name__ == "__main__":
    pytest.main([__file__])
