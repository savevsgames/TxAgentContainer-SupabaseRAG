# TxAgent Medical RAG System: Complete Technical Breakdown

## System Overview

The TxAgent Medical RAG System is a comprehensive medical document processing and question-answering platform that combines GPU-accelerated BioBERT embeddings with OpenAI's GPT models for accurate medical text analysis. The system is designed with a hybrid architecture that separates compute-intensive operations from user-facing services.

## Architecture Components

### 1. Frontend Application (React/Vite)
- **Purpose**: User interface for document upload and chat interactions
- **Technology**: React with Vite, TypeScript, Tailwind CSS
- **Authentication**: Supabase Auth with JWT tokens
- **Features**:
  - Document upload with drag-and-drop interface
  - Real-time chat interface with medical AI assistant
  - User authentication and session management
  - File management and processing status tracking

### 2. Node.js Backend (Render.com)
- **Purpose**: API gateway and business logic orchestration
- **Technology**: Node.js, Express, Supabase client
- **Responsibilities**:
  - User authentication and session management
  - File upload handling to Supabase Storage
  - Orchestrating calls to TxAgent GPU container
  - Database operations and user data management
  - CORS handling for frontend requests

### 3. TxAgent GPU Container (RunPod)
- **Purpose**: GPU-accelerated document processing and embedding generation
- **Technology**: Python, FastAPI, BioBERT, PyTorch, CUDA
- **Location**: `hybrid-agent/` directory
- **Key Features**:
  - BioBERT model for medical text embeddings (768 dimensions)
  - Document processing (PDF, DOCX, TXT, MD)
  - Vector similarity search using pgvector
  - OpenAI GPT integration for response generation
  - JWT authentication with Supabase tokens

### 4. Database & Storage (Supabase)
- **Purpose**: Data persistence and vector storage
- **Technology**: PostgreSQL with pgvector extension
- **Components**:
  - User authentication and management
  - Document storage (Supabase Storage)
  - Vector embeddings storage with similarity search
  - Row Level Security (RLS) for data isolation
  - Background job tracking

## Data Flow Architecture

### Document Processing Flow
1. **Upload**: User uploads document via frontend
2. **Storage**: Node.js backend stores file in Supabase Storage
3. **Processing**: Backend calls TxAgent container `/embed` endpoint
4. **Extraction**: TxAgent downloads file, extracts text
5. **Embedding**: BioBERT generates 768-dimensional embeddings
6. **Storage**: Embeddings stored in Supabase with user isolation
7. **Completion**: Job status updated, user notified

### Chat Query Flow
1. **Query**: User submits question via frontend
2. **Authentication**: JWT token validated by TxAgent
3. **Embedding**: Query converted to BioBERT embedding
4. **Search**: Vector similarity search in user's documents
5. **Context**: Relevant document chunks retrieved
6. **Generation**: OpenAI GPT generates contextual response
7. **Response**: Answer with sources returned to user

## Database Schema

### Core Tables

#### `documents`
```sql
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content TEXT NOT NULL,
  embedding VECTOR(768),
  metadata JSONB DEFAULT '{}'::JSONB,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

#### `embedding_jobs`
```sql
CREATE TABLE embedding_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  file_path TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  metadata JSONB DEFAULT '{}'::JSONB,
  chunk_count INTEGER DEFAULT 0,
  error TEXT,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

#### `agents`
```sql
CREATE TABLE agents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  status TEXT DEFAULT 'initializing',
  session_data JSONB DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  last_active TIMESTAMPTZ DEFAULT now(),
  terminated_at TIMESTAMPTZ
);
```

### Security Features
- **Row Level Security (RLS)**: All tables enforce user-based data isolation
- **JWT Authentication**: Supabase tokens with `aud: "authenticated"` validation
- **Foreign Key Constraints**: Ensure data integrity and cascade deletions
- **Indexed Queries**: Optimized vector similarity search with IVFFlat indexing

## TxAgent Container Details

### Core Components

#### 1. Document Processing (`embedder.py`)
- **Text Extraction**: 
  - PDF: PyMuPDF (fitz) for robust text extraction
  - DOCX: python-docx for structured document parsing
  - TXT/MD: Direct UTF-8 decoding
- **Chunking Strategy**: 
  - Chunk size: 512 words
  - Overlap: 50 words for context preservation
  - Metadata preservation for source tracking

#### 2. BioBERT Embedding Engine
- **Model**: `dmis-lab/biobert-v1.1` (medical domain-specific)
- **Dimensions**: 768-dimensional embeddings
- **Hardware**: CUDA-accelerated on NVIDIA GPUs
- **Optimization**: Batch processing with memory management

#### 3. Vector Search (`match_documents` function)
```sql
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding VECTOR(768),
  match_threshold FLOAT,
  match_count INT,
  query_user_id UUID
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
)
```

#### 4. Authentication System (`auth.py`)
- **JWT Validation**: Supabase token verification with audience validation
- **Security Features**:
  - Signature verification using `SUPABASE_JWT_SECRET`
  - Audience validation: `"aud": "authenticated"`
  - Expiration checking with clock skew tolerance
  - Comprehensive error logging for debugging

#### 5. LLM Integration (`llm.py`)
- **Provider**: OpenAI GPT-4 Turbo
- **Features**: 
  - Streaming responses
  - Context-aware prompting
  - Temperature control for response variability
  - Fallback handling when OpenAI is unavailable

### API Endpoints

#### `POST /embed`
**Purpose**: Process and embed documents
**Authentication**: Required (JWT)
**Payload**:
```json
{
  "file_path": "documents/user123/file.pdf",
  "metadata": {
    "title": "Medical Research Paper",
    "author": "Dr. Smith",
    "category": "cardiology"
  }
}
```
**Response**:
```json
{
  "job_id": "uuid-string",
  "status": "pending",
  "message": "Document is being processed"
}
```

#### `POST /chat`
**Purpose**: Generate responses based on document context
**Authentication**: Required (JWT)
**Payload**:
```json
{
  "query": "What are the treatment options for hypertension?",
  "top_k": 5,
  "temperature": 0.7
}
```
**Response**:
```json
{
  "response": "Based on your documents, treatment options include...",
  "sources": [
    {
      "content": "Document excerpt...",
      "metadata": {"title": "Hypertension Guidelines"},
      "similarity": 0.85
    }
  ],
  "status": "success"
}
```

#### `GET /embedding-jobs/{job_id}`
**Purpose**: Check processing status
**Authentication**: Required (JWT)
**Response**:
```json
{
  "job_id": "uuid-string",
  "status": "completed",
  "chunk_count": 15,
  "document_ids": ["doc-id-1", "doc-id-2"],
  "message": "Processing completed successfully"
}
```

#### `GET /health`
**Purpose**: Container health check
**Authentication**: Not required
**Response**:
```json
{
  "status": "healthy",
  "model": "dmis-lab/biobert-v1.1",
  "device": "cuda",
  "version": "1.0.0"
}
```

## Environment Configuration

### TxAgent Container Environment Variables
```bash
# Supabase Configuration
SUPABASE_URL=https://bfjfjxzdjhraabputkqi.supabase.co
SUPABASE_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...  # anon key
SUPABASE_SERVICE_ROLE_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...  # service role
SUPABASE_JWT_SECRET=aGA7EVBjss...ZwVtVtDQ==  # Critical for JWT validation
SUPABASE_STORAGE_BUCKET=documents

# BioBERT Model Configuration
MODEL_NAME=dmis-lab/biobert-v1.1
EMBEDDING_DIMENSION=768
DEVICE=cuda
MAX_TOKENS=512

# Processing Configuration
CHUNK_SIZE=512
CHUNK_OVERLAP=50
LOG_LEVEL=INFO

# OpenAI Configuration (Optional)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4-turbo-preview

# FastAPI Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=False
```

## Hardware Requirements

### Minimum Specifications
- **GPU**: NVIDIA T4 (16GB VRAM)
- **RAM**: 16GB system memory
- **CPU**: 4 cores
- **Storage**: 20GB for model cache and temporary files

### Recommended Specifications
- **GPU**: NVIDIA A100 (40GB+ VRAM)
- **RAM**: 32GB system memory
- **CPU**: 8+ cores
- **Storage**: 50GB SSD

### Performance Metrics
- **A100**: ~2ms per chunk embedding, ~1000 pages/minute
- **T4**: ~10ms per chunk embedding, ~200 pages/minute
- **CPU Fallback**: ~50ms per chunk embedding, ~40 pages/minute

## Security Architecture

### Authentication Flow
1. **Frontend**: User authenticates with Supabase Auth
2. **JWT Generation**: Supabase generates signed JWT with user claims
3. **Token Transmission**: JWT sent in Authorization header
4. **Container Validation**: TxAgent validates JWT signature and audience
5. **User Context**: User ID extracted for RLS enforcement

### Data Isolation
- **Row Level Security**: Database-level user data isolation
- **JWT Claims**: User ID from `sub` claim for ownership verification
- **Storage Isolation**: User-specific file paths in Supabase Storage
- **API Isolation**: All endpoints require valid user authentication

### Security Best Practices
- **JWT Secret Management**: Secure environment variable handling
- **HTTPS Enforcement**: All communications encrypted in transit
- **Input Validation**: Comprehensive request payload validation
- **Error Handling**: Secure error messages without information leakage
- **Audit Logging**: Comprehensive request/response logging for security monitoring

## Deployment Architecture

### Container Deployment (RunPod)
- **Base Image**: `nvidia/cuda:12.1.1-runtime-ubuntu22.04`
- **Python Environment**: Virtual environment with isolated dependencies
- **Model Caching**: Persistent volume for HuggingFace model cache
- **Health Monitoring**: Built-in health checks and logging
- **Auto-scaling**: GPU resource allocation based on demand

### Backend Deployment (Render.com)
- **Runtime**: Node.js with Express framework
- **Environment**: Production-optimized with environment variables
- **CORS Configuration**: Configured for frontend domain access
- **Health Monitoring**: Built-in health endpoints and logging

### Database Deployment (Supabase)
- **Managed PostgreSQL**: Fully managed with automatic backups
- **Extensions**: pgvector for vector operations
- **Scaling**: Automatic scaling based on usage
- **Security**: Built-in RLS and authentication

## Monitoring and Observability

### Logging Strategy
- **Structured Logging**: JSON-formatted logs with consistent schema
- **Request Tracing**: Complete request/response lifecycle tracking
- **Performance Metrics**: Processing times and resource utilization
- **Error Tracking**: Comprehensive error logging with stack traces
- **Security Events**: Authentication and authorization event logging

### Key Metrics
- **Processing Latency**: Document embedding and query response times
- **Throughput**: Documents processed per minute
- **Error Rates**: Failed requests and processing errors
- **Resource Utilization**: GPU memory and compute usage
- **User Activity**: Authentication events and API usage patterns

## Development and Testing

### Local Development Setup
1. **Container Development**: Docker Compose for local GPU testing
2. **Backend Development**: Node.js with local Supabase connection
3. **Frontend Development**: Vite dev server with hot reload
4. **Database Development**: Local Supabase instance or cloud connection

### Testing Strategy
- **Unit Tests**: Core functionality testing for each component
- **Integration Tests**: End-to-end workflow testing
- **Performance Tests**: Load testing for scalability validation
- **Security Tests**: Authentication and authorization validation
- **API Tests**: Comprehensive Postman collection for endpoint validation

### Postman Testing Collection
The included Postman collection provides comprehensive API testing:
- Health checks and connectivity validation
- Authentication flow testing
- Document embedding workflow
- Chat query functionality
- Error handling validation
- Performance benchmarking

## Future Enhancements

### Planned Features
- **Multi-Model Support**: Additional embedding models for specialized domains
- **Streaming Responses**: Real-time response generation for chat
- **Advanced Caching**: Intelligent caching for frequently accessed documents
- **Custom Model Training**: Fine-tuning capabilities for specific medical domains
- **Batch Processing**: Bulk document processing capabilities

### Optimization Opportunities
- **Model Quantization**: Reduced memory usage with maintained accuracy
- **Dynamic Batching**: Optimized throughput for concurrent requests
- **Parallel Processing**: Multi-GPU support for increased throughput
- **Memory Optimization**: Improved memory management for large documents

## Support and Maintenance

### Monitoring Dashboards
- **System Health**: Real-time container and service status
- **Performance Metrics**: Processing times and throughput analytics
- **Error Tracking**: Centralized error monitoring and alerting
- **User Analytics**: Usage patterns and feature adoption

### Maintenance Procedures
- **Model Updates**: Regular BioBERT model updates and validation
- **Dependency Management**: Security updates and version management
- **Performance Optimization**: Regular performance tuning and optimization
- **Backup and Recovery**: Automated backup procedures and disaster recovery

This comprehensive system provides a robust, scalable, and secure platform for medical document processing and AI-powered question answering, with clear separation of concerns and optimized performance for each component.