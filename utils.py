import logging
import os
import time
from typing import Dict, List, Any, Tuple, Optional, Callable, TypeVar
from functools import wraps
import json
import numpy as np
import torch
from sklearn.metrics.pairwise import cosine_similarity
import traceback
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("utils")

T = TypeVar('T')

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

def calculate_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """
    Calculate cosine similarity between two embeddings.
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        
    Returns:
        Cosine similarity score (0-1)
    """
    # Convert to numpy arrays
    vec1 = np.array(embedding1).reshape(1, -1)
    vec2 = np.array(embedding2).reshape(1, -1)
    
    # Calculate cosine similarity
    return float(cosine_similarity(vec1, vec2)[0][0])

def format_sources(sources: List[Dict[str, Any]]) -> str:
    """
    Format source documents for display.
    
    Args:
        sources: List of source documents with metadata
        
    Returns:
        Formatted sources as string
    """
    if not sources:
        return "No sources available."
    
    formatted = []
    for i, source in enumerate(sources, 1):
        metadata = source.get("metadata", {})
        source_info = f"Source {i}: "
        
        if "title" in metadata:
            source_info += metadata["title"]
        elif "source_file" in metadata:
            source_info += os.path.basename(metadata["source_file"])
        else:
            source_info += "Unknown source"
            
        if "page" in metadata:
            source_info += f" (Page {metadata['page']})"
            
        similarity = source.get("similarity", None)
        if similarity is not None:
            source_info += f" - Relevance: {similarity:.2f}"
            
        formatted.append(source_info)
        
    return "\n".join(formatted)

def check_gpu_availability() -> Tuple[bool, str]:
    """
    Check if GPU is available and return device info.
    
    Returns:
        Tuple of (is_available, device_info)
    """
    if torch.cuda.is_available():
        cuda_device_count = torch.cuda.device_count()
        cuda_device_name = torch.cuda.get_device_name(0) if cuda_device_count > 0 else "Unknown"
        return True, f"CUDA available: {cuda_device_count} device(s), using {cuda_device_name}"
    else:
        return False, "CUDA not available, using CPU"

def serialize_embeddings(embeddings: List[float]) -> str:
    """
    Serialize embeddings for storage.
    
    Args:
        embeddings: List of floating-point values
        
    Returns:
        Serialized embeddings as string
    """
    return json.dumps(embeddings)

def deserialize_embeddings(serialized: str) -> List[float]:
    """
    Deserialize embeddings from storage.
    
    Args:
        serialized: Serialized embeddings string
        
    Returns:
        List of floating-point values
    """
    return json.loads(serialized)

@measure_time
def batch_process(items: List[Any], batch_size: int, process_func: Callable, *args, **kwargs) -> List[Any]:
    """
    Process items in batches.
    
    Args:
        items: List of items to process
        batch_size: Batch size
        process_func: Function to process a batch
        
    Returns:
        List of processed results
    """
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_results = process_func(batch, *args, **kwargs)
        results.extend(batch_results)
    return results

def validate_file_type(file_path: str) -> bool:
    """
    Validate if file type is supported.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if supported, False otherwise
    """
    supported_extensions = {'.pdf', '.docx', '.txt', '.md'}
    return os.path.splitext(file_path)[1].lower() in supported_extensions

class DocumentProcessingError(Exception):
    """Custom exception for document processing errors."""
    pass

class EmbeddingError(Exception):
    """Custom exception for embedding generation errors."""
    pass

class StorageError(Exception):
    """Custom exception for storage operations errors."""
    pass