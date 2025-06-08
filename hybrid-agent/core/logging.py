"""
Comprehensive logging system for TxAgent.

This module provides structured logging for requests, authentication events,
system events, and performance metrics with user context tracking.
"""

import logging
import os
import time
import traceback
from typing import Dict, List, Any, Optional, Callable, TypeVar
from functools import wraps
from datetime import datetime

T = TypeVar('T')

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


class RequestLogger:
    """Enhanced logging utility for tracking user interactions and system events."""
    
    def __init__(self, service_name: str = "TxAgent"):
        self.service_name = service_name
        self.logger = logging.getLogger(f"{service_name.lower()}_requests")
        
    def log_request_start(self, endpoint: str, method: str, user_context: Dict[str, Any] = None, request_data: Dict[str, Any] = None):
        """Log the start of a request with user context."""
        user_info = self._extract_user_info(user_context)
        
        self.logger.info(
            f"🚀 REQUEST_START",
            extra={
                "event_type": "request_start",
                "endpoint": endpoint,
                "method": method,
                "user_id": user_info.get("user_id"),
                "user_email": user_info.get("email"),
                "user_role": user_info.get("role"),
                "request_size": len(str(request_data)) if request_data else 0,
                "timestamp": datetime.utcnow().isoformat(),
                "service": self.service_name
            }
        )
        
    def log_request_success(self, endpoint: str, method: str, user_context: Dict[str, Any] = None, 
                          response_data: Dict[str, Any] = None, processing_time: float = None):
        """Log successful request completion."""
        user_info = self._extract_user_info(user_context)
        
        self.logger.info(
            f"✅ REQUEST_SUCCESS",
            extra={
                "event_type": "request_success",
                "endpoint": endpoint,
                "method": method,
                "user_id": user_info.get("user_id"),
                "user_email": user_info.get("email"),
                "processing_time_ms": round(processing_time * 1000, 2) if processing_time else None,
                "response_size": len(str(response_data)) if response_data else 0,
                "timestamp": datetime.utcnow().isoformat(),
                "service": self.service_name
            }
        )
        
    def log_request_error(self, endpoint: str, method: str, error: Exception, 
                         user_context: Dict[str, Any] = None, request_data: Dict[str, Any] = None):
        """Log request errors with full context."""
        user_info = self._extract_user_info(user_context)
        
        self.logger.error(
            f"❌ REQUEST_ERROR",
            extra={
                "event_type": "request_error",
                "endpoint": endpoint,
                "method": method,
                "user_id": user_info.get("user_id"),
                "user_email": user_info.get("email"),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "error_traceback": traceback.format_exc(),
                "request_data": str(request_data)[:500] if request_data else None,
                "timestamp": datetime.utcnow().isoformat(),
                "service": self.service_name
            }
        )
        
    def log_auth_event(self, event_type: str, user_context: Dict[str, Any] = None, 
                      success: bool = True, details: Dict[str, Any] = None):
        """Log authentication-related events."""
        user_info = self._extract_user_info(user_context)
        
        log_level = self.logger.info if success else self.logger.warning
        status_emoji = "🔐" if success else "🚫"
        
        log_level(
            f"{status_emoji} AUTH_{event_type.upper()}",
            extra={
                "event_type": f"auth_{event_type}",
                "user_id": user_info.get("user_id"),
                "user_email": user_info.get("email"),
                "user_role": user_info.get("role"),
                "success": success,
                "details": details,
                "timestamp": datetime.utcnow().isoformat(),
                "service": self.service_name
            }
        )
        
    def log_system_event(self, event_type: str, details: Dict[str, Any] = None, level: str = "info"):
        """Log system-level events."""
        log_func = getattr(self.logger, level.lower(), self.logger.info)
        emoji_map = {
            "startup": "🚀",
            "shutdown": "🛑",
            "health_check": "💓",
            "model_load": "🧠",
            "database_connection": "🗄️",
            "error": "💥",
            "warning": "⚠️"
        }
        
        emoji = emoji_map.get(event_type, "ℹ️")
        
        log_func(
            f"{emoji} SYSTEM_{event_type.upper()}",
            extra={
                "event_type": f"system_{event_type}",
                "details": details,
                "timestamp": datetime.utcnow().isoformat(),
                "service": self.service_name
            }
        )
        
    def log_performance_metric(self, operation: str, duration: float, user_context: Dict[str, Any] = None,
                             metadata: Dict[str, Any] = None):
        """Log performance metrics."""
        user_info = self._extract_user_info(user_context)
        
        self.logger.info(
            f"📊 PERFORMANCE_METRIC",
            extra={
                "event_type": "performance_metric",
                "operation": operation,
                "duration_ms": round(duration * 1000, 2),
                "user_id": user_info.get("user_id"),
                "metadata": metadata,
                "timestamp": datetime.utcnow().isoformat(),
                "service": self.service_name
            }
        )
        
    def _extract_user_info(self, user_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Extract user information from context."""
        if not user_context:
            return {"user_id": None, "email": None, "role": None}
            
        return {
            "user_id": user_context.get("sub") or user_context.get("user_id"),
            "email": user_context.get("email"),
            "role": user_context.get("role", "authenticated")
        }


# Global request logger instance
request_logger = RequestLogger("TxAgent")


def log_request(endpoint: str = None):
    """Decorator to automatically log request start/end with user context."""
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            endpoint_name = endpoint or func.__name__
            
            # Extract user context from kwargs if available
            user_context = kwargs.get('user_context') or kwargs.get('current_user')
            request_data = kwargs.get('request') or kwargs.get('data')
            
            request_logger.log_request_start(
                endpoint=endpoint_name,
                method="POST",  # Most of our endpoints are POST
                user_context=user_context,
                request_data=request_data.__dict__ if hasattr(request_data, '__dict__') else None
            )
            
            try:
                result = await func(*args, **kwargs)
                processing_time = time.time() - start_time
                
                request_logger.log_request_success(
                    endpoint=endpoint_name,
                    method="POST",
                    user_context=user_context,
                    response_data=result.__dict__ if hasattr(result, '__dict__') else None,
                    processing_time=processing_time
                )
                
                return result
            except Exception as e:
                request_logger.log_request_error(
                    endpoint=endpoint_name,
                    method="POST",
                    error=e,
                    user_context=user_context,
                    request_data=request_data.__dict__ if hasattr(request_data, '__dict__') else None
                )
                raise
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            start_time = time.time()
            endpoint_name = endpoint or func.__name__
            
            user_context = kwargs.get('user_context') or kwargs.get('current_user')
            request_data = kwargs.get('request') or kwargs.get('data')
            
            request_logger.log_request_start(
                endpoint=endpoint_name,
                method="POST",
                user_context=user_context,
                request_data=request_data.__dict__ if hasattr(request_data, '__dict__') else None
            )
            
            try:
                result = func(*args, **kwargs)
                processing_time = time.time() - start_time
                
                request_logger.log_request_success(
                    endpoint=endpoint_name,
                    method="POST",
                    user_context=user_context,
                    response_data=result.__dict__ if hasattr(result, '__dict__') else None,
                    processing_time=processing_time
                )
                
                return result
            except Exception as e:
                request_logger.log_request_error(
                    endpoint=endpoint_name,
                    method="POST",
                    error=e,
                    user_context=user_context,
                    request_data=request_data.__dict__ if hasattr(request_data, '__dict__') else None
                )
                raise
                
        # Return appropriate wrapper based on whether function is async
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator