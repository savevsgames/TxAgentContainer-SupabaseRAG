"""
Custom exception classes for TxAgent.

This module defines all custom exceptions used throughout the application
for better error handling and debugging.
"""

class DocumentProcessingError(Exception):
    """Custom exception for document processing errors."""
    pass


class EmbeddingError(Exception):
    """Custom exception for embedding generation errors."""
    pass


class StorageError(Exception):
    """Custom exception for storage operations errors."""
    pass