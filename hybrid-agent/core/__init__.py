"""
Core services package for TxAgent.

This package provides centralized services for:
- Authentication and JWT handling
- Logging and monitoring
- Input validation
- Custom exceptions
- Performance decorators
"""

# Re-export everything to maintain backward compatibility
from .logging import *
from .decorators import *
from .validators import *
from .exceptions import *

__all__ = [
    # Logging utilities
    'RequestLogger',
    'request_logger',
    'log_request',
    
    # Decorators
    'with_retry',
    'measure_time',
    
    # Validators
    'validate_file_type',
    'calculate_similarity',
    'format_sources',
    'check_gpu_availability',
    'serialize_embeddings',
    'deserialize_embeddings',
    'batch_process',
    
    # Exceptions
    'DocumentProcessingError',
    'EmbeddingError',
    'StorageError',
]