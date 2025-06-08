# Supabase Database Configuration - UPDATED ✅

## Status: CLEAN AND OPERATIONAL

✅ **SUCCESS**: The database schema has been consolidated and is now fully operational with the latest migration.

## Database Overview

The TxAgent Medical RAG system uses PostgreSQL with the `pgvector` extension for vector similarity search. All tables implement Row Level Security (RLS) to ensure users can only access their own data.

**Current Migration**: `supabase/migrations/20250608104059_warm_silence.sql`

## Extensions Required

```sql
-- Required for vector operations
CREATE EXTENSION IF NOT EXISTS vector;
```

## Current Clean Database Schema

### Tables

#### 1. `documents` Table

Stores document chunks with their 768-dimensional BioBERT embeddings for similarity search.

```sql
CREATE TABLE public.documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  filename TEXT,                                    -- Added for function compatibility
  content TEXT NOT NULL,                           -- Document chunk content
  embedding VECTOR(768),                           -- BioBERT embedding
  metadata JSONB DEFAULT '{}'::JSONB,              -- Chunk metadata
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

**Key Features**:
- **768-dimensional vectors**: Compatible with BioBERT model
- **User isolation**: RLS policies filter by `user_id`
- **Metadata storage**: JSON metadata for chunk information
- **Performance indexes**: IVFFlat index for fast vector search

**Indexes**:
```sql
CREATE INDEX documents_user_id_idx ON public.documents(user_id);
CREATE INDEX documents_embedding_idx ON public.documents 
  USING ivfflat (embedding vector_cosine_ops) WITH (lists='100');
```

#### 2. `embedding_jobs` Table

Tracks the status of document processing jobs handled by the TxAgent container.

```sql
CREATE TABLE public.embedding_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  file_path TEXT NOT NULL,                         -- Path in Supabase Storage
  status TEXT NOT NULL DEFAULT 'pending',          -- Job status
  metadata JSONB DEFAULT '{}'::JSONB,              -- Job metadata
  chunk_count INTEGER DEFAULT 0,                   -- Number of chunks created
  error TEXT,                                      -- Error message if failed
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

**Status Values**:
- `pending`: Job created, waiting for processing
- `processing`: Currently being processed by TxAgent
- `completed`: Successfully processed and stored
- `failed`: Processing failed (see error field)

**Indexes**:
```sql
CREATE INDEX embedding_jobs_user_id_idx ON public.embedding_jobs(user_id);
CREATE INDEX embedding_jobs_status_idx ON public.embedding_jobs(status);
```

#### 3. `agents` Table

Manages TxAgent container sessions and their lifecycle.

```sql
CREATE TABLE public.agents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  status TEXT DEFAULT 'initializing',              -- Agent status
  session_data JSONB DEFAULT '{}'::JSONB,          -- Session configuration
  created_at TIMESTAMPTZ DEFAULT now(),
  last_active TIMESTAMPTZ DEFAULT now(),
  terminated_at TIMESTAMPTZ                        -- When agent was terminated
);
```

**Status Values**:
- `initializing`: Agent session being created
- `active`: Agent ready for operations
- `idle`: Agent inactive but available
- `terminated`: Agent session ended

**Indexes**:
```sql
CREATE INDEX agents_user_id_idx ON public.agents(user_id);
CREATE INDEX agents_status_idx ON public.agents(status);
CREATE INDEX agents_last_active_idx ON public.agents(last_active);
```

## Row Level Security (RLS)

All tables have RLS enabled with user-specific access policies based on the consolidated migration.

### RLS Policies

```sql
-- Enable RLS on all tables
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.embedding_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agents ENABLE ROW LEVEL SECURITY;

-- User isolation policies
CREATE POLICY "documents_user_isolation" ON public.documents
  FOR ALL TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "embedding_jobs_user_isolation" ON public.embedding_jobs
  FOR ALL TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "agents_user_isolation" ON public.agents
  FOR ALL TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);
```

**Key Features**:
- **Automatic filtering**: Users only see their own data
- **Insert protection**: Users can only create records for themselves
- **Update protection**: Users can only modify their own records
- **Delete protection**: Users can only delete their own records

## Database Functions

### `match_documents` Function

The standardized vector similarity search function that respects RLS policies.

```sql
CREATE OR REPLACE FUNCTION public.match_documents(
  query_embedding VECTOR(768),
  match_threshold FLOAT DEFAULT 0.5,
  match_count INTEGER DEFAULT 5
) RETURNS TABLE (
  id UUID,
  filename TEXT,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
) 
LANGUAGE plpgsql
SECURITY INVOKER
STABLE
AS $$
BEGIN
  RETURN QUERY
  SELECT
    d.id,
    COALESCE(d.filename, 'Unknown') as filename,
    d.content,
    COALESCE(d.metadata, '{}'::jsonb) as metadata,
    (1 - (d.embedding <=> query_embedding))::float as similarity
  FROM public.documents d
  WHERE d.embedding IS NOT NULL
    AND d.content IS NOT NULL
    AND (1 - (d.embedding <=> query_embedding)) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$;
```

**Key Features**:
- **`SECURITY INVOKER`**: Respects RLS policies automatically
- **User filtering**: Only returns documents the user can access
- **Cosine similarity**: Uses `<=>` operator for vector distance
- **Configurable**: Threshold and count parameters
- **Performance optimized**: Uses vector indexes

**Permissions**:
```sql
GRANT EXECUTE ON FUNCTION public.match_documents(VECTOR(768), FLOAT, INTEGER) TO authenticated;
```

## Authentication Requirements

### JWT Token Structure

For RLS policies to work correctly, JWT tokens must have these claims:

```json
{
  "sub": "user-uuid-here",           // REQUIRED: User ID
  "aud": "authenticated",            // REQUIRED: Audience
  "role": "authenticated",           // REQUIRED: Role
  "email": "user@example.com",       // Optional: User email
  "exp": 1234567890,                 // REQUIRED: Expiration
  "iat": 1234567890                  // Optional: Issued at
}
```

**Critical Requirements**:
- `sub`: Must match `user_id` in database tables
- `aud`: Must be "authenticated" for RLS policies
- `role`: Must be "authenticated" for RLS policies
- `exp`: Token must not be expired

### Environment Variables

**Required for TxAgent Container**:
```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key  # Optional fallback
SUPABASE_JWT_SECRET=your-jwt-secret                       # CRITICAL for validation
SUPABASE_STORAGE_BUCKET=documents
```

## Storage Configuration

### Buckets

- **`documents`**: Stores uploaded files (PDF, DOCX, TXT, MD)
  - **Public access**: No (private bucket)
  - **File size limit**: 50MB per file
  - **Allowed MIME types**: 
    - `application/pdf`
    - `application/vnd.openxmlformats-officedocument.wordprocessingml.document`
    - `text/plain`
    - `text/markdown`

### Storage Policies

```sql
-- Users can upload to their own folder
CREATE POLICY "Users can upload their own files"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'documents' AND auth.uid()::text = (storage.foldername(name))[1]);

-- Users can read their own files
CREATE POLICY "Users can read their own files"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'documents' AND auth.uid()::text = (storage.foldername(name))[1]);

-- Users can delete their own files
CREATE POLICY "Users can delete their own files"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'documents' AND auth.uid()::text = (storage.foldername(name))[1]);
```

## Application Integration

### Centralized Authentication Service

The application now uses a centralized authentication service (`core/auth_service.py`) that:

1. **Validates JWT tokens** with proper error handling
2. **Creates authenticated Supabase clients** with correct headers
3. **Manages user context** for RLS compliance
4. **Provides consistent error handling** across all endpoints

### Usage Example

```python
from core.auth_service import auth_service

# Get authenticated client
client = auth_service.get_authenticated_client(jwt_token)

# Perform database operations (RLS automatically applied)
result = client.table("documents").select("*").execute()

# Call vector search function
search_results = client.rpc("match_documents", {
    "query_embedding": embedding,
    "match_threshold": 0.5,
    "match_count": 5
}).execute()
```

## Data Flow

### Document Processing Flow
1. **Upload**: User uploads document to Supabase Storage
2. **Job Creation**: Embedding job created in `embedding_jobs` table
3. **Processing**: TxAgent downloads file and processes it
4. **Chunking**: Text split into overlapping chunks
5. **Embedding**: BioBERT generates 768-dimensional embeddings
6. **Storage**: Chunks and embeddings stored in `documents` table
7. **Completion**: Job status updated to "completed"

### Chat Query Flow
1. **Authentication**: JWT token validated and user context established
2. **Embedding**: Query converted to BioBERT embedding
3. **Search**: `match_documents` function performs similarity search
4. **Filtering**: RLS automatically filters to user's documents only
5. **Response**: Relevant chunks returned with similarity scores
6. **Generation**: LLM generates response based on context

## Performance Optimization

### Vector Search Performance

The IVFFlat index provides fast approximate nearest neighbor search:

```sql
CREATE INDEX documents_embedding_idx ON public.documents 
  USING ivfflat (embedding vector_cosine_ops) WITH (lists='100');
```

**Configuration**:
- **Lists**: 100 (good for up to 1M vectors)
- **Distance**: Cosine distance (`<=>` operator)
- **Probes**: Default (can be tuned with `SET ivfflat.probes = N`)

### Query Optimization

- **User filtering**: RLS policies use indexed `user_id` column
- **Vector search**: IVFFlat index for fast similarity search
- **Content filtering**: Non-null checks on `embedding` and `content`
- **Result limiting**: `LIMIT` clause prevents large result sets

## Monitoring and Maintenance

### Key Metrics to Monitor

1. **Vector search performance**: Query execution times
2. **Index usage**: IVFFlat index hit rates
3. **RLS policy performance**: User filtering efficiency
4. **Storage usage**: Document and embedding storage growth
5. **Authentication success rates**: JWT validation metrics

### Maintenance Tasks

1. **Index maintenance**: Monitor and rebuild IVFFlat indexes if needed
2. **Storage cleanup**: Remove orphaned files and embeddings
3. **Performance tuning**: Adjust IVFFlat parameters based on data size
4. **Security audits**: Review RLS policies and JWT validation

## Troubleshooting

### Common Issues

1. **RLS Policy Violations**
   - **Cause**: JWT token missing required claims
   - **Solution**: Verify `sub`, `aud`, and `role` claims in JWT
   - **Check**: Ensure `auth.uid()` returns correct user ID

2. **Vector Search Errors**
   - **Cause**: Function signature mismatch or missing permissions
   - **Solution**: Use standardized function signature
   - **Check**: Verify `GRANT EXECUTE` permissions

3. **Authentication Failures**
   - **Cause**: Invalid JWT secret or expired tokens
   - **Solution**: Verify `SUPABASE_JWT_SECRET` environment variable
   - **Check**: Token expiration and signature validation

### Debug Queries

```sql
-- Check if auth.uid() works
SELECT auth.uid();

-- Check user's documents
SELECT COUNT(*) FROM documents;

-- Test vector search function
SELECT * FROM match_documents(
  ARRAY[0.1, 0.2, ...]::vector(768),
  0.5,
  5
);

-- Check RLS policies
SELECT * FROM pg_policies WHERE tablename = 'documents';
```

## Summary

The database is now in a clean, optimized state with:

✅ **Single consolidated migration** - No more duplicate objects
✅ **Standardized function signatures** - Consistent API
✅ **Proper RLS implementation** - Secure user isolation
✅ **Centralized authentication** - Consistent JWT handling
✅ **Performance optimization** - Proper indexes and query patterns
✅ **Comprehensive documentation** - Clear usage guidelines

The system is ready for production use with proper authentication, security, and performance characteristics.