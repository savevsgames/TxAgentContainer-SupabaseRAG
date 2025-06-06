# TxAgent Hybrid Container: Technical Breakdown

## Architecture Overview

The TxAgent Hybrid Container is a GPU-accelerated medical document processing and RAG (Retrieval-Augmented Generation) system that combines BioBERT embeddings with OpenAI's GPT models for accurate medical text analysis and question answering.

### Core Components

1. **Document Processor**
   - Handles PDF, DOCX, TXT, and MD files
   - Uses PyMuPDF (v1.22.0) for PDF extraction
   - Uses python-docx (v0.8.11) for DOCX handling
   - Implements chunking with configurable overlap

2. **Embedding Engine**
   - BioBERT model (dmis-lab/biobert-v1.1)
   - PyTorch (v2.0.0+) backend
   - 768-dimensional embeddings
   - Batched processing support

3. **Vector Storage**
   - Supabase pgvector integration
   - Cosine similarity search
   - Row Level Security (RLS) enabled
   - Indexed for performance

4. **LLM Integration**
   - OpenAI GPT-4 Turbo
   - Streaming support
   - Context-aware prompting
   - Temperature control

## Dependencies & Versions

### Core Libraries
```
torch>=2.0.0          # GPU acceleration, CUDA support
transformers>=4.30.0  # BioBERT model handling
fastapi>=0.95.0      # API framework, async support
uvicorn>=0.22.0      # ASGI server
supabase>=1.0.3      # Database & storage
pgvector>=0.2.0      # Vector operations
```

### Document Processing
```
PyMuPDF>=1.22.0      # PDF extraction, memory efficient
python-docx>=0.8.11  # DOCX handling
```

### Utilities
```
python-dotenv>=1.0.0 # Environment management
pydantic>=2.0.0     # Data validation
tenacity>=8.2.2     # Retry logic
numpy>=1.24.0       # Array operations
scikit-learn>=1.2.0 # Similarity calculations
```

## Configuration Parameters

### BioBERT Settings
- `MODEL_NAME`: dmis-lab/biobert-v1.1
- `EMBEDDING_DIMENSION`: 768
- `MAX_TOKENS`: 512 (per chunk)
- `CHUNK_SIZE`: 512
- `CHUNK_OVERLAP`: 50

### Processing Settings
- `BATCH_SIZE`: 32 (for embedding)
- `RETRY_ATTEMPTS`: 3
- `BACKOFF_FACTOR`: 2.0
- `MAX_RETRIES`: 3

### API Settings
- `WORKERS`: 1 (per container)
- `TIMEOUT`: 300 seconds
- `MAX_UPLOAD_SIZE`: 100MB

## Hardware Requirements

### Minimum Specifications
- GPU: NVIDIA T4 (16GB VRAM)
- RAM: 16GB
- CPU: 4 cores
- Storage: 20GB

### Recommended Specifications
- GPU: NVIDIA A100 (40GB VRAM)
- RAM: 32GB
- CPU: 8 cores
- Storage: 50GB

### Scaling Considerations
- One GPU can handle ~100 concurrent embedding jobs
- Memory usage scales with chunk size and batch size
- A100 can process ~1000 pages/minute
- T4 can process ~200 pages/minute

## Performance Metrics

### Embedding Performance
- A100: ~2ms per chunk
- T4: ~10ms per chunk
- CPU: ~50ms per chunk

### Document Processing
- PDF extraction: ~100ms/page
- DOCX extraction: ~50ms/document
- Average embedding job: 2-5 seconds

## Security Features

1. **Authentication**
   - JWT validation
   - Supabase RLS integration
   - Service role separation

2. **Data Protection**
   - Temporary file cleanup
   - Memory wiping
   - Secure file downloads

3. **Access Control**
   - User-scoped queries
   - Resource limits
   - Rate limiting

## Monitoring & Logging

### Log Levels
- DEBUG: Detailed processing info
- INFO: Standard operations
- WARNING: Non-critical issues
- ERROR: Critical failures

### Metrics Tracked
- Job completion rates
- Processing times
- Error frequencies
- Resource usage

## Deployment Recommendations

### Container Settings
```yaml
resources:
  limits:
    nvidia.com/gpu: 1
    memory: 32Gi
  requests:
    nvidia.com/gpu: 1
    memory: 16Gi
```

### Environment Optimization
- CUDA 12.1+
- cuDNN 8.9+
- Ubuntu 22.04 LTS

### Scaling Strategy
1. Vertical: Upgrade to A100 for 5x performance
2. Horizontal: Add containers for parallel processing
3. Memory: Adjust batch size based on VRAM

## Common Issues & Solutions

1. **Memory Errors**
   - Reduce batch size
   - Enable gradient checkpointing
   - Clear CUDA cache between jobs

2. **Timeout Issues**
   - Increase worker timeout
   - Add connection pooling
   - Implement chunked uploads

3. **Performance Bottlenecks**
   - Enable CUDA optimization
   - Use mixed precision
   - Optimize chunk size

## Development Guidelines

1. **Code Structure**
   - Modular components
   - Clear error handling
   - Comprehensive logging
   - Type hints

2. **Testing**
   - Unit tests for core functions
   - Integration tests for API
   - Load testing for scaling
   - Error scenario coverage

3. **Maintenance**
   - Regular model updates
   - Dependency audits
   - Performance monitoring
   - Error rate tracking

## Future Enhancements

1. **Planned Features**
   - Multi-model support
   - Streaming embeddings
   - Advanced caching
   - Custom model training

2. **Optimization Opportunities**
   - Quantization support
   - Dynamic batching
   - Parallel processing
   - Memory optimization

## Support & Resources

- Documentation: Full API specs
- Logs: Structured JSON format
- Metrics: Prometheus compatible
- Traces: OpenTelemetry support

## License & Attribution

- Open source components
- Model licenses
- Usage restrictions
- Citation requirements