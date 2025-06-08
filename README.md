# TxAgent Medical RAG System

A comprehensive medical document processing and question-answering platform that combines GPU-accelerated BioBERT embeddings with OpenAI's GPT models for accurate medical text analysis.

## System Overview

The TxAgent Medical RAG System uses a hybrid architecture that separates compute-intensive operations from user-facing services:

- **Frontend**: React/Vite application for document upload and chat
- **Backend**: Node.js API gateway on Render.com
- **TxAgent Container**: GPU-accelerated document processing on RunPod
- **Database**: Supabase PostgreSQL with pgvector for vector storage

## Quick Start

### Prerequisites

- NVIDIA GPU with CUDA support (for TxAgent container)
- Supabase project with pgvector extension enabled
- Node.js 18+ (for backend)
- Docker (for container deployment)

### Environment Setup

1. **Supabase Configuration**
   ```bash
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-supabase-anon-key
   SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
   SUPABASE_JWT_SECRET=your-supabase-jwt-secret
   SUPABASE_STORAGE_BUCKET=documents
   ```

2. **TxAgent Container**
   ```bash
   MODEL_NAME=dmis-lab/biobert-v1.1
   EMBEDDING_DIMENSION=768
   DEVICE=cuda
   OPENAI_API_KEY=your-openai-api-key
   ```

### Database Setup

✅ **COMPLETED**: The database schema has been consolidated into a single migration file:
- Run `supabase/migrations/20250108120000_consolidated_schema.sql`
- This creates all required tables, indexes, RLS policies, and functions
- No additional migrations needed

### Deployment

1. **TxAgent Container** → RunPod with GPU
2. **Backend** → Render.com
3. **Frontend** → Render.com or Netlify
4. **Database** → Supabase (managed)

## Architecture Components

### TxAgent Container (`hybrid-agent/`)

GPU-accelerated container for document processing and embedding generation.

**Key Features:**
- BioBERT model for medical text embeddings (768 dimensions)
- Document processing (PDF, DOCX, TXT, MD)
- Vector similarity search using pgvector
- OpenAI GPT integration for response generation
- JWT authentication with Supabase tokens

**API Endpoints:**
- `GET /health` - Container health check
- `POST /embed` - Process and embed documents
- `POST /chat` - Generate responses based on document context
- `GET /embedding-jobs/{job_id}` - Check processing status

### Database Schema

#### Core Tables

**documents**
```sql
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  filename TEXT,
  content TEXT NOT NULL,
  embedding VECTOR(768),
  metadata JSONB DEFAULT '{}'::JSONB,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

**embedding_jobs**
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

**agents**
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

## Data Flow

### Document Processing Flow
1. User uploads document via frontend
2. Backend stores file in Supabase Storage
3. Backend calls TxAgent container `/embed` endpoint
4. TxAgent downloads file, extracts text, generates embeddings
5. Embeddings stored in Supabase with user isolation
6. Job status updated, user notified

### Chat Query Flow
1. User submits question via frontend
2. JWT token validated by TxAgent
3. Query converted to BioBERT embedding
4. Vector similarity search using `match_documents()` function
5. OpenAI GPT generates contextual response
6. Answer with sources returned to user

## API Reference

### TxAgent Container Endpoints

#### POST /embed
Process and embed a document from Supabase Storage.

**Headers:**
```
Authorization: Bearer <supabase_jwt_token>
Content-Type: application/json
```

**Request:**
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

**Response:**
```json
{
  "job_id": "uuid-string",
  "status": "pending",
  "message": "Document is being processed"
}
```

#### POST /chat
Generate responses based on document context.

**Headers:**
```
Authorization: Bearer <supabase_jwt_token>
Content-Type: application/json
```

**Request:**
```json
{
  "query": "What are the treatment options for hypertension?",
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
      "metadata": {"title": "Hypertension Guidelines"},
      "similarity": 0.85
    }
  ],
  "status": "success"
}
```

## Authentication & Security

### JWT Token Requirements

The TxAgent container uses a simplified authentication approach:

1. **JWT Validation**: Tokens are validated using the `SUPABASE_JWT_SECRET`
2. **Manual Header Setting**: JWT tokens are passed via `Authorization` header to Supabase client
3. **RLS Enforcement**: Row Level Security policies automatically filter data by user

**Critical JWT Claims**:
- `sub`: User ID (UUID) - **MUST match user_id in database**
- `aud`: Must be "authenticated" - **REQUIRED for RLS policies**
- `role`: Must be "authenticated" - **REQUIRED for RLS policies**
- `exp`: Token expiration timestamp
- `iat`: Token issued at timestamp

## Testing

### Postman Collection

Import `TxAgent_API_Tests.postman_collection.json` for comprehensive API testing:

1. Health checks and connectivity validation
2. Authentication flow testing
3. Document embedding workflow
4. Chat query functionality
5. Error handling validation

### Getting JWT Tokens

For testing authenticated endpoints:

1. **From Frontend**: Check browser localStorage for `supabase.auth.token`
2. **Manual Generation**:
   ```javascript
   const { data } = await supabase.auth.signInWithPassword({
     email: 'user@example.com',
     password: 'password'
   });
   console.log('JWT:', data.session.access_token);
   ```

## Troubleshooting

### Common Issues

1. **405 Method Not Allowed**
   - Verify endpoint exists and HTTP method is correct
   - Check CORS configuration

2. **401 Unauthorized**
   - Verify JWT token is valid and not expired
   - Check Authorization header format: `Bearer <token>`
   - Ensure user exists in Supabase

3. **500 Internal Server Error**
   - Check container logs for detailed error information
   - Verify environment variables are set correctly
   - Check Supabase connection and database schema

### Database Migration Status

✅ **RESOLVED**: Migration consolidation completed successfully
- All duplicate migration files have been removed
- Single consolidated migration provides clean schema
- No more duplicate functions or RLS policy conflicts

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

## Development

### Local Development

1. **Container Development**: Use Docker Compose for local GPU testing
2. **Backend Development**: Node.js with local Supabase connection
3. **Frontend Development**: Vite dev server with hot reload

### File Organization

The project follows a modular architecture:

```
├── hybrid-agent/          # TxAgent container
│   ├── main.py            # FastAPI application
│   ├── embedder.py        # Document processing and embedding
│   ├── auth.py            # JWT authentication
│   ├── llm.py             # OpenAI integration
│   └── utils.py           # Utilities and logging
├── supabase/
│   └── migrations/        # Single consolidated migration
└── docs/                  # Documentation
```

### Testing Strategy

- **Unit Tests**: Core functionality testing
- **Integration Tests**: End-to-end workflow testing
- **API Tests**: Comprehensive Postman collection
- **Performance Tests**: Load testing for scalability

## Support

- **Documentation**: Complete API specs and troubleshooting guides
- **Logs**: Structured JSON format with user context
- **Health Checks**: Real-time service monitoring
- **Error Tracking**: Centralized error monitoring

For detailed technical information, see:
- `BREAKDOWN.md` - Complete technical breakdown
- `SUPABASE_MIGRATIONS.md` - Migration consolidation details (COMPLETED)
- `SUPABASE_CONFIG.md` - Database configuration details