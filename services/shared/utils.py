"""
Shared Utilities

This module contains utility functions and helpers used across all services.
"""

import logging
import time
import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
import json


def setup_logging(service_name: str, log_level: str = "INFO") -> logging.Logger:
    """
    Set up logging for a service.
    
    Args:
        service_name: Name of the service
        log_level: Logging level
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(service_name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Create console handler with a more detailed format
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            f'%(asctime)s - {service_name} - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def timing_decorator(func: Callable) -> Callable:
    """
    Decorator to measure function execution time.
    
    Args:
        func: Function to be timed
        
    Returns:
        Wrapped function with timing capability
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger = logging.getLogger(func.__module__)
            logger.info(f"{func.__name__} executed in {execution_time:.3f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger = logging.getLogger(func.__module__)
            logger.error(f"{func.__name__} failed after {execution_time:.3f} seconds: {e}")
            raise
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger = logging.getLogger(func.__module__)
            logger.info(f"{func.__name__} executed in {execution_time:.3f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger = logging.getLogger(func.__module__)
            logger.error(f"{func.__name__} failed after {execution_time:.3f} seconds: {e}")
            raise
    
    return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper


def retry_decorator(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator to retry function execution on failure.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Backoff multiplier for delay
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            current_delay = delay
            logger = logging.getLogger(func.__module__)
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        logger.error(f"{func.__name__} failed after {max_retries} retries: {e}")
                        raise
                    
                    logger.warning(f"{func.__name__} attempt {attempt + 1} failed: {e}. Retrying in {current_delay:.1f}s...")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            current_delay = delay
            logger = logging.getLogger(func.__module__)
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        logger.error(f"{func.__name__} failed after {max_retries} retries: {e}")
                        raise
                    
                    logger.warning(f"{func.__name__} attempt {attempt + 1} failed: {e}. Retrying in {current_delay:.1f}s...")
                    time.sleep(current_delay)
                    current_delay *= backoff
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def validate_request_data(required_fields: List[str], optional_fields: Optional[List[str]] = None) -> Callable:
    """
    Decorator to validate request data.
    
    Args:
        required_fields: List of required field names
        optional_fields: List of optional field names
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Assume request_data is the first argument after self
            if len(args) >= 2 and isinstance(args[1], dict):
                request_data = args[1]
            elif 'request_data' in kwargs:
                request_data = kwargs['request_data']
            else:
                raise ValueError("No request_data found in function arguments")
            
            # Check required fields
            missing_fields = [field for field in required_fields if field not in request_data]
            if missing_fields:
                raise ValueError(f"Missing required fields: {missing_fields}")
            
            # Optionally validate field types or values here
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def format_response(status: str = "success", data: Any = None, error: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Format a standard API response.
    
    Args:
        status: Response status ("success" or "error")
        data: Response data
        error: Error message if status is "error"
        **kwargs: Additional response fields
        
    Returns:
        Formatted response dictionary
    """
    response = {
        "status": status,
        "timestamp": datetime.now().isoformat()
    }
    
    if status == "success" and data is not None:
        response["data"] = data
    elif status == "error" and error:
        response["error"] = error
    
    # Add any additional fields
    response.update(kwargs)
    
    return response


def safe_json_serialize(obj: Any) -> str:
    """
    Safely serialize an object to JSON, handling datetime and other non-serializable types.
    
    Args:
        obj: Object to serialize
        
    Returns:
        JSON string
    """
    def default_serializer(o):
        if isinstance(o, datetime):
            return o.isoformat()
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")
    
    return json.dumps(obj, default=default_serializer, indent=2)


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """
    Calculate percentage change between two values.
    
    Args:
        old_value: Original value
        new_value: New value
        
    Returns:
        Percentage change
    """
    if old_value == 0:
        return 0.0 if new_value == 0 else float('inf')
    
    return ((new_value - old_value) / old_value) * 100


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of specified size.
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def get_nested_value(data: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Get a nested value from a dictionary using dot notation.
    
    Args:
        data: Dictionary to search
        key_path: Dot-separated key path (e.g., "user.profile.name")
        default: Default value if key not found
        
    Returns:
        Value at the key path or default
    """
    keys = key_path.split('.')
    current = data
    
    try:
        for key in keys:
            current = current[key]
        return current
    except (KeyError, TypeError):
        return default


def set_nested_value(data: Dict[str, Any], key_path: str, value: Any) -> None:
    """
    Set a nested value in a dictionary using dot notation.
    
    Args:
        data: Dictionary to modify
        key_path: Dot-separated key path
        value: Value to set
    """
    keys = key_path.split('.')
    current = data
    
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    current[keys[-1]] = value


class CircularBuffer:
    """
    A simple circular buffer implementation for storing recent data.
    """
    
    def __init__(self, maxsize: int):
        """
        Initialize circular buffer.
        
        Args:
            maxsize: Maximum size of the buffer
        """
        self.maxsize = maxsize
        self.buffer: List[Any] = []
        self.index = 0
    
    def append(self, item: Any) -> None:
        """
        Add an item to the buffer.
        
        Args:
            item: Item to add
        """
        if len(self.buffer) < self.maxsize:
            self.buffer.append(item)
        else:
            self.buffer[self.index] = item
            self.index = (self.index + 1) % self.maxsize
    
    def get_all(self) -> List[Any]:
        """
        Get all items in the buffer in order.
        
        Returns:
            List of items in chronological order
        """
        if len(self.buffer) < self.maxsize:
            return self.buffer.copy()
        else:
            return self.buffer[self.index:] + self.buffer[:self.index]
    
    def get_latest(self, n: int = 1) -> List[Any]:
        """
        Get the latest n items.
        
        Args:
            n: Number of latest items to get
            
        Returns:
            List of latest items
        """
        all_items = self.get_all()
        return all_items[-n:] if n <= len(all_items) else all_items
    
    def size(self) -> int:
        """Get current size of buffer."""
        return len(self.buffer)
    
    def is_full(self) -> bool:
        """Check if buffer is full."""
        return len(self.buffer) == self.maxsize
