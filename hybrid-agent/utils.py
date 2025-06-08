"""
Core utilities for TxAgent.

This module contains essential utility functions that don't fit into
other specialized modules. Most utilities have been moved to the
core package for better organization.
"""

import os
import logging

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("utils")

# Import everything from core modules for backward compatibility
from .core import *

# Keep only essential utilities here that don't belong elsewhere
def get_environment_info():
    """Get current environment information."""
    return {
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "device": os.getenv("DEVICE", "cpu"),
        "model_name": os.getenv("MODEL_NAME", "dmis-lab/biobert-v1.1"),
        "embedding_dimension": int(os.getenv("EMBEDDING_DIMENSION", "768")),
        "chunk_size": int(os.getenv("CHUNK_SIZE", "512")),
        "chunk_overlap": int(os.getenv("CHUNK_OVERLAP", "50"))
    }