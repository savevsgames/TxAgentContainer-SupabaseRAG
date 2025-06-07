# TxAgent Hybrid Container

Medical RAG Vector Uploader with BioBERT embeddings and chat capabilities.

## Overview

This container provides a hybrid approach to medical document processing, embedding, and retrieval. It integrates with Supabase for storage and vector search, enabling both direct vector database access via Row Level Security (RLS) and backend-proxied interactions.

## Features

- BioBERT-based document embedding
- Vector storage and querying via Supabase pgvector
- Document processing for multiple formats (.pdf, .docx, .txt, .md)
- JWT authentication with Supabase
- Optional RAG chat pipeline
- FastAPI endpoints for embedding, chat, and health checking
- **Comprehensive logging system for debugging and monitoring**

## Prerequisites

- NVIDIA GPU with CUDA support
- Supabase project with pgvector extension enabled
- Supabase storage bucket for document storage

## Environment Variables

Copy `.env.example` to `.env` and configure:

```
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
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

### Health Check

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "model": "dmis-lab/biobert-v1.1",
  "device": "cuda",
  "version": "1.0.0"
}
```

### Embed Document

```
POST /embed
```

Headers:
```
Authorization: Bearer <supabase_jwt_token>
Content-Type: application/json
```

Request:
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

Response:
```json
{
  "job_id": "uuid-string",
  "status": "pending",
  "message": "Document is being processed in the background"
}
```

### Get Job Status

```
GET /embedding-jobs/{job_id}
```

Headers:
```
Authorization: Bearer <supabase_jwt_token>
```

Response:
```json
{
  "job_id": "uuid-string",
  "status": "completed",
  "chunk_count": 15,
  "document_ids": ["doc-id-1", "doc-id-2"],
  "message": "Job status: completed"
}
```

### Chat

```
POST /chat
```

Headers:
```
Authorization: Bearer <supabase_jwt_token>
Content-Type: application/json
```

Request:
```json
{
  "query": "What treatments are available for lung cancer?",
  "history": [],
  "top_k": 5,
  "temperature": 0.7
}
```

Response:
```json
{
  "response": "Based on the medical literature...",
  "sources": [
    {
      "content": "Document excerpt...",
      "metadata": {"title": "Cancer Treatment Guide"},
      "similarity": 0.85
    }
  ],
  "status": "success"
}
```

### Test Endpoints

```
GET /test    - Test GET method
POST /test   - Test POST method
```

## Testing with Postman

### 1. Import the Postman Collection

Save the following as `TxAgent_API_Tests.postman_collection.json`:

```json
{
  "info": {
    "name": "TxAgent API Tests",
    "description": "Test collection for TxAgent Hybrid Container",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "variable": [
    {
      "key": "base_url",
      "value": "https://bjo5yophw94s7b-8000.proxy.runpod.net",
      "type": "string"
    },
    {
      "key": "jwt_token",
      "value": "your_supabase_jwt_token_here",
      "type": "string"
    }
  ],
  "item": [
    {
      "name": "Health Check",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{base_url}}/health",
          "host": ["{{base_url}}"],
          "path": ["health"]
        }
      }
    },
    {
      "name": "Test GET",
      "request": {
        "method": "GET",
        "header": [],
        "url": {
          "raw": "{{base_url}}/test",
          "host": ["{{base_url}}"],
          "path": ["test"]
        }
      }
    },
    {
      "name": "Test POST",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"test\": \"data\",\n  \"timestamp\": \"2025-01-01T00:00:00Z\"\n}"
        },
        "url": {
          "raw": "{{base_url}}/test",
          "host": ["{{base_url}}"],
          "path": ["test"]
        }
      }
    },
    {
      "name": "Embed Document",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{jwt_token}}"
          },
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"file_path\": \"test-document.pdf\",\n  \"metadata\": {\n    \"title\": \"Test Document\",\n    \"author\": \"Test Author\",\n    \"category\": \"test\"\n  }\n}"
        },
        "url": {
          "raw": "{{base_url}}/embed",
          "host": ["{{base_url}}"],
          "path": ["embed"]
        }
      }
    },
    {
      "name": "Chat Query",
      "request": {
        "method": "POST",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{jwt_token}}"
          },
          {
            "key": "Content-Type",
            "value": "application/json"
          }
        ],
        "body": {
          "mode": "raw",
          "raw": "{\n  \"query\": \"What is the main topic of the documents?\",\n  \"top_k\": 5,\n  \"temperature\": 0.7\n}"
        },
        "url": {
          "raw": "{{base_url}}/chat",
          "host": ["{{base_url}}"],
          "path": ["chat"]
        }
      }
    },
    {
      "name": "Get Job Status",
      "request": {
        "method": "GET",
        "header": [
          {
            "key": "Authorization",
            "value": "Bearer {{jwt_token}}"
          }
        ],
        "url": {
          "raw": "{{base_url}}/embedding-jobs/{{job_id}}",
          "host": ["{{base_url}}"],
          "path": ["embedding-jobs", "{{job_id}}"]
        }
      }
    }
  ]
}
```

### 2. Getting a Supabase JWT Token

To test endpoints that require authentication, you need a valid Supabase JWT token:

#### Option A: From Your Frontend Application
1. Open browser developer tools on your frontend
2. Go to Application/Storage → Local Storage
3. Look for `supabase.auth.token` or similar
4. Copy the JWT token value

#### Option B: Using Supabase CLI (if available)
```bash
supabase auth login
supabase projects list
supabase auth token
```

#### Option C: Manual Token Generation (for testing)
```javascript
// Run this in your browser console on a page with Supabase client
const { data, error } = await supabase.auth.signInWithPassword({
  email: 'your-email@example.com',
  password: 'your-password'
});
console.log('JWT Token:', data.session.access_token);
```

### 3. Testing Steps

1. **Import the collection** into Postman
2. **Set the variables**:
   - `base_url`: `https://bjo5yophw94s7b-8000.proxy.runpod.net`
   - `jwt_token`: Your actual Supabase JWT token
3. **Run tests in order**:
   - Health Check (should work without auth)
   - Test GET (should work without auth)
   - Test POST (should work without auth)
   - Embed Document (requires auth)
   - Chat Query (requires auth)

### 4. Expected Results

- **Health Check**: Should return 200 with service info
- **Test endpoints**: Should return 200 with test messages
- **Embed Document**: Should return 202 with job_id
- **Chat Query**: Should return 200 with response and sources

## Logging System

The container includes comprehensive logging for debugging:

### Log Types

1. **Request Logs**: All HTTP requests with user context
2. **Authentication Logs**: JWT validation and user identification
3. **System Events**: Startup, model loading, background tasks
4. **Performance Metrics**: Processing times and resource usage
5. **Error Logs**: Detailed error information with stack traces

### Log Format

All logs include:
- Timestamp
- Event type
- User context (ID, email, role)
- Request/response details
- Performance metrics
- Error information

### Viewing Logs

Check your RunPod container logs to see detailed information about:
- User interactions
- Authentication events
- Processing times
- Error details
- System health

## Troubleshooting

### Common Issues

1. **405 Method Not Allowed**
   - Check if the endpoint exists in the logs
   - Verify the HTTP method (GET vs POST)
   - Check CORS configuration

2. **401 Unauthorized**
   - Verify JWT token is valid and not expired
   - Check Authorization header format: `Bearer <token>`
   - Ensure user exists in Supabase

3. **500 Internal Server Error**
   - Check container logs for detailed error information
   - Verify environment variables are set correctly
   - Check Supabase connection

### Debug Commands

```bash
# Check container logs
docker logs <container_id>

# Test health endpoint
curl https://bjo5yophw94s7b-8000.proxy.runpod.net/health

# Test with authentication
curl -X POST https://bjo5yophw94s7b-8000.proxy.runpod.net/test \
  -H "Authorization: Bearer <your_jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

## Required Supabase Setup

1. Enable pgvector extension
2. Create the following tables and functions:

```sql
-- Enable pgvector extension
create extension if not exists vector;

-- Documents table with RLS
create table documents (
  id uuid primary key default gen_random_uuid(),
  content text not null,
  embedding vector(768),
  metadata jsonb default '{}'::jsonb,
  user_id uuid references auth.users(id) on delete cascade not null,
  created_at timestamp with time zone default now()
);

-- Embedding jobs table
create table embedding_jobs (
  id uuid primary key default gen_random_uuid(),
  file_path text not null,
  status text default 'pending',
  metadata jsonb default '{}'::jsonb,
  chunk_count integer default 0,
  error text,
  user_id uuid references auth.users(id) on delete cascade not null,
  created_at timestamp with time zone default now(),
  updated_at timestamp with time zone default now()
);

-- Enable RLS
alter table documents enable row level security;
alter table embedding_jobs enable row level security;

-- Create policies
create policy "Users can read their own documents"
on documents for select
using (auth.uid() = user_id);

create policy "Users can insert their own documents"
on documents for insert
with check (auth.uid() = user_id);

create policy "Users can read their own embedding jobs"
on embedding_jobs for select
using (auth.uid() = user_id);

create policy "Users can insert their own embedding jobs"
on embedding_jobs for insert
with check (auth.uid() = user_id);

create policy "Users can update their own embedding jobs"
on embedding_jobs for update
using (auth.uid() = user_id);

-- Function for similarity search
create or replace function match_documents(
  query_embedding vector(768),
  match_threshold float,
  match_count int,
  query_user_id uuid
)
returns table (
  id uuid,
  content text,
  metadata jsonb,
  similarity float
)
language sql stable
as $$
  select
    documents.id,
    documents.content,
    documents.metadata,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where 1 - (documents.embedding <=> query_embedding) > match_threshold
    and documents.user_id = query_user_id
  order by similarity desc
  limit match_count;
$$;
```

## Integration with Node.js Backend

The Node.js backend should be configured with CORS to allow requests from your frontend domain:

```javascript
// In your Node.js backend
app.use(cors({
  origin: [
    'https://medical-rag-vector-uploader-1.onrender.com',
    'https://your-frontend-domain.com',
    'http://localhost:3000' // for development
  ],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));
```

## Security Considerations

- JWT authentication is required for all endpoints except health and test
- Row Level Security ensures users can only access their own documents
- Service role key is used for administrative operations
- All requests are logged with user context for audit trails

## Performance Monitoring

The logging system tracks:
- Request processing times
- Model inference times
- Database query performance
- Memory and GPU usage
- Error rates and types

## Support & Resources

- Documentation: Full API specs in this README
- Logs: Structured JSON format with user context
- Metrics: Performance and usage tracking
- Health Checks: Real-time service monitoring