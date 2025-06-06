import logging
import os
import time
from typing import Dict, List, Any, Tuple, Optional
import json
import numpy as np
import torch
from sklearn.metrics.pairwise import cosine_similarity

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("utils")

def measure_time(func):
    """Decorator to measure execution time of functions."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logger.debug(f"{func.__name__} executed in {end_time - start_time:.2f} seconds")
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
def batch_process(items: List[Any], batch_size: int, process_func, *args, **kwargs) -> List[Any]:
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