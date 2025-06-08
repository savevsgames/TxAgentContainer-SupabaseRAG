"""
Performance and retry decorators for TxAgent.

This module provides decorators for retry logic, performance monitoring,
and other cross-cutting concerns.
"""

import time
import logging
from typing import Callable, TypeVar
from functools import wraps

from .logging import request_logger

T = TypeVar('T')

logger = logging.getLogger(__name__)


def with_retry(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Retry decorator with exponential backoff and enhanced logging.
    
    Args:
        retries: Maximum number of retries
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            current_delay = delay
            last_exception = None
            
            for attempt in range(retries + 1):
                try:
                    result = func(*args, **kwargs)
                    if attempt > 0:
                        request_logger.log_system_event(
                            "retry_success",
                            details={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "total_attempts": retries + 1
                            }
                        )
                    return result
                except exceptions as e:
                    last_exception = e
                    if attempt == retries:
                        request_logger.log_system_event(
                            "retry_failed",
                            details={
                                "function": func.__name__,
                                "total_attempts": retries + 1,
                                "final_error": str(e)
                            },
                            level="error"
                        )
                        raise
                    
                    request_logger.log_system_event(
                        "retry_attempt",
                        details={
                            "function": func.__name__,
                            "attempt": attempt + 1,
                            "error": str(e),
                            "retry_delay": current_delay
                        },
                        level="warning"
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        return wrapper
    return decorator


def measure_time(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to measure execution time of functions with enhanced logging."""
    @wraps(func)
    def wrapper(*args, **kwargs) -> T:
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        duration = end_time - start_time
        
        request_logger.log_performance_metric(
            operation=func.__name__,
            duration=duration,
            metadata={
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys()) if kwargs else []
            }
        )
        
        return result
    return wrapper