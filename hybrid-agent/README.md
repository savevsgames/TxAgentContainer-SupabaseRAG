# TxAgent Hybrid Container

Medical RAG Vector Uploader with BioBERT embeddings and chat capabilities.

## Overview

This container provides a hybrid approach to medical document processing, embedding, and retrieval. It integrates with Supabase for storage and vector search, enabling both direct vector database access via Row Level Security (RLS) and backend-proxied interactions.

## Features

- BioBERT-based document embedding (768 dimensions)
- Vector storage and querying via Supabase pgvector
- Document processing for multiple formats (.pdf, .docx, .txt, .md)
- JWT authentication with Supabase
- Optional RAG chat pipeline with OpenAI GPT integration
- FastAPI endpoints for embedding, chat, and health checking

## Prerequisites

- NVIDIA GPU with CUDA support
- Supabase project with pgvector extension enabled
- Supabase storage bucket for document storage

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_JWT_SECRET=your-supabase-jwt-secret
SUPABASE_STORAGE_BUCKET=documents

# BioBERT Model Configuration
MODEL_NAME=dmis-lab/biobert-v1.1
EMBEDDING_DIMENSION=768
DEVICE=cuda
MAX_TOKENS=512

# FastAPI Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=False

# Container Configuration
LOG_LEVEL=INFO
CHUNK_SIZE=512
CHUNK_OVERLAP=50

# OpenAI Configuration (Optional)
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4-turbo-preview
```

## Build and Run

### Build Docker Image

```bash
docker build -t txagent-hybrid .
```

### Run Container

```bash
docker run --gpus all -p 8000:8000 --env-file .env txagent-hybrid
```

### Deploy to RunPod

1. Push the image to a Docker registry
2. Create a RunPod template with the image
3. Deploy on an A100 80GB GPU instance

## API Endpoints

### Embed Document

```
POST /embed
```

**Headers:**
```
Authorization: Bearer <supabase_jwt_token>
Content-Type: application/json
```

**Request:**
```json
{
  "file_path": "path/to/document.pdf",
  "metadata": {
    "title": "Medical Research Paper",
    "author": "Dr. Smith",
    "category": "oncology"
  }
}
```

**Response:**
```json
{
  "job_id": "uuid-string",
  "status": "pending",
  "message": "Document is being processed"
}
```

### Chat

```
POST /chat
```

**Headers:**
```
Authorization: Bearer <supabase_jwt_token>
Content-Type: application/json
```

**Request:**
```json
{
  "query": "What treatments are available for lung cancer?",
  "top_k": 5,
  "temperature": 0.7
}
```

**Response:**
```json
{
  "response": "Based on your documents, treatment options include...",
  "sources": [
    {
      "content": "Document excerpt...",
      "metadata": {"title": "Cancer Treatment Guidelines"},
      "similarity": 0.85
    }
  ],
  "status": "success"
}
```

### Check Job Status

```
GET /embedding-jobs/{job_id}
```

**Headers:**
```
Authorization: Bearer <supabase_jwt_token>
```

**Response:**
```json
{
  "job_id": "uuid-string",
  "status": "completed",
  "chunk_count": 15,
  "document_ids": ["doc-id-1", "doc-id-2"],
  "message": "Processing completed successfully"
}
```

### Health Check

```
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "model": "dmis-lab/biobert-v1.1",
  "device": "cuda",
  "version": "1.0.0"
}
```

## Authentication

The container uses JWT tokens from Supabase for authentication:

1. **Token Validation**: JWT tokens are validated using `SUPABASE_JWT_SECRET`
2. **User Context**: User ID is extracted from the `sub` claim
3. **RLS Enforcement**: Row Level Security policies automatically filter data by user
4. **Header Setting**: JWT tokens are passed directly to Supabase client via Authorization header

### Current Authentication Implementation

```python
def _get_supabase_client(self, jwt: Optional[str] = None) -> Client:
    if jwt:
        client = create_client(supabase_url, supabase_key)
        # Set Authorization header directly for RLS
        client.auth._headers = {"Authorization": f"Bearer {jwt}"}
        return client
    else:
        return self.supabase
```

This simplified approach ensures that JWT tokens properly establish user context for RLS policies.

## Required Supabase Setup

1. Enable pgvector extension
2. Create the required tables and functions (see `../SUPABASE_MIGRATIONS.md` for consolidated setup)

### Core Database Objects

**Tables:**
- `documents` - Store document content and embeddings
- `embedding_jobs` - Track document processing jobs
- `agents` - Manage agent sessions

**Functions:**
- `match_documents(vector, float, integer)` - Vector similarity search with RLS

**Security:**
- Row Level Security enabled on all tables
- User isolation via `auth.uid()` policies
- JWT token authentication

## Document Processing Flow

1. **Upload**: Document uploaded to Supabase Storage
2. **Job Creation**: Embedding job record created in database
3. **Processing**: Document downloaded and text extracted
4. **Chunking**: Text split into overlapping chunks (512 words, 50 word overlap)
5. **Embedding**: BioBERT generates 768-dimensional embeddings for each chunk
6. **Storage**: Embeddings stored in `documents` table with user isolation
7. **Completion**: Job status updated to "completed"

## Chat Query Flow

1. **Query**: User submits question
2. **Authentication**: JWT token validated and user ID extracted
3. **Embedding**: Query converted to BioBERT embedding
4. **Search**: Vector similarity search using `match_documents()` function
5. **Context**: Relevant document chunks retrieved (filtered by RLS)
6. **Generation**: OpenAI GPT generates response based on context
7. **Response**: Answer returned with source citations

## Integrating with Your Application

1. When a user uploads a document to Supabase Storage, call the `/embed` endpoint with the file path
2. The container will process the document and store embeddings in the `documents` table
3. For RAG queries, call the `/chat` endpoint with the user's query
4. The container will find relevant document chunks and generate a response

## Troubleshooting

### Common Issues

1. **RLS Policy Violations**
   - Ensure JWT tokens have correct `sub`, `aud`, and `role` claims
   - Verify `SUPABASE_JWT_SECRET` is correctly set
   - Check that user exists in Supabase auth.users table

2. **Function Not Found Errors**
   - Ensure `match_documents` function exists with correct signature
   - Run consolidated migration to fix duplicate functions
   - Verify pgvector extension is enabled

3. **Authentication Failures**
   - Check JWT token format and expiration
   - Verify Authorization header format: `Bearer <token>`
   - Ensure Supabase environment variables are correct

### Debug Commands

```bash
# Check container health
curl https://your-container-url/health

# Test with authentication
curl -X POST https://your-container-url/chat \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'
```

### Logs Analysis

The container provides comprehensive logging:
- **Request/Response**: All API calls with user context
- **Authentication**: JWT validation and user identification
- **Processing**: Document processing and embedding generation
- **Errors**: Detailed error information with stack traces

## Performance

### Hardware Requirements

**Minimum:**
- GPU: NVIDIA T4 (16GB VRAM)
- RAM: 16GB system memory
- CPU: 4 cores

**Recommended:**
- GPU: NVIDIA A100 (40GB+ VRAM)
- RAM: 32GB system memory
- CPU: 8+ cores

### Performance Metrics
- **A100**: ~2ms per chunk embedding, ~1000 pages/minute
- **T4**: ~10ms per chunk embedding, ~200 pages/minute

## Security Considerations

- JWT authentication is required for all endpoints except `/health`
- Row Level Security ensures users can only access their own documents
- Service role key is used for administrative operations
- All communications should use HTTPS in production
- Environment variables contain sensitive information and should be secured

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run the application
python main.py
```

### Testing

Use the included Postman collection (`../TxAgent_API_Tests.postman_collection.json`) for comprehensive API testing.

## Support

For issues and questions:
- Check the logs for detailed error information
- Verify environment variables are correctly set
- Ensure Supabase database schema is properly configured
- See `../SUPABASE_MIGRATIONS.md` for database setup issues