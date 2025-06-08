# Supabase Database Configuration

This document provides a comprehensive overview of the Supabase database schema, policies, and functions for the Medical RAG Vector Uploader system.

## Database Overview

The system uses PostgreSQL with the `pgvector` extension for vector similarity search. All tables implement Row Level Security (RLS) to ensure users can only access their own data.

## Extensions

```sql
-- Required extensions
CREATE EXTENSION IF NOT EXISTS vector;
```

## Tables Schema

### 1. `documents` Table

Stores document chunks with their vector embeddings for similarity search.

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

**Columns:**
- `id`: Unique identifier for each document chunk
- `content`: The actual text content of the document chunk
- `embedding`: 768-dimensional vector embedding (BioBERT)
- `metadata`: JSON metadata (title, author, chunk_index, etc.)
- `user_id`: Foreign key to Supabase auth.users table
- `created_at`: Timestamp when the document was created

**Indexes:**
```sql
CREATE INDEX documents_embedding_idx ON documents
USING ivfflat (embedding vector_cosine_ops) WITH (lists='100');

CREATE INDEX documents_user_id_idx ON documents(user_id);
```

### 2. `embedding_jobs` Table

Tracks the status of document embedding jobs processed by the TxAgent container.

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

**Columns:**
- `id`: Unique identifier for the embedding job
- `file_path`: Path to the file in Supabase Storage
- `status`: Job status (`pending`, `processing`, `completed`, `failed`)
- `metadata`: JSON metadata including document IDs created
- `chunk_count`: Number of document chunks created
- `error`: Error message if job failed
- `user_id`: Foreign key to Supabase auth.users table
- `created_at`: Timestamp when job was created
- `updated_at`: Timestamp when job was last updated

**Indexes:**
```sql
CREATE INDEX embedding_jobs_user_id_idx ON embedding_jobs(user_id);
CREATE INDEX embedding_jobs_status_idx ON embedding_jobs(status);
```

### 3. `agents` Table

Manages TxAgent container sessions and their status.

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

**Columns:**
- `id`: Unique identifier for the agent session
- `user_id`: Foreign key to Supabase auth.users table
- `status`: Agent status (`initializing`, `active`, `idle`, `terminated`)
- `session_data`: JSON data including container_id, endpoint_url, capabilities
- `created_at`: Timestamp when agent session was created
- `last_active`: Timestamp of last agent activity
- `terminated_at`: Timestamp when agent was terminated

**Indexes:**
```sql
CREATE INDEX agents_user_id_idx ON agents(user_id);
CREATE INDEX agents_status_idx ON agents(status);
CREATE INDEX agents_last_active_idx ON agents(last_active);
```

**Constraints:**
```sql
ALTER TABLE agents ADD CONSTRAINT agents_status_check 
CHECK (status = ANY (ARRAY['initializing'::text, 'active'::text, 'idle'::text, 'terminated'::text]));
```

**Triggers:**
```sql
CREATE TRIGGER update_agents_last_active 
BEFORE UPDATE ON agents 
FOR EACH ROW 
EXECUTE FUNCTION update_agent_last_active();
```

## Row Level Security (RLS) Policies

All tables have RLS enabled with user-specific access policies.

### Documents Table Policies

```sql
-- Enable RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Users can insert their own documents
CREATE POLICY "Users can insert their own documents"
  ON documents
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

-- Users can read their own documents
CREATE POLICY "Users can read their own documents"
  ON documents
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- Users can update their own documents
CREATE POLICY "Users can update their own documents"
  ON documents
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Users can delete their own documents
CREATE POLICY "Users can delete their own documents"
  ON documents
  FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);
```

### Embedding Jobs Table Policies

```sql
-- Enable RLS
ALTER TABLE embedding_jobs ENABLE ROW LEVEL SECURITY;

-- Users can insert their own embedding jobs
CREATE POLICY "Users can insert their own embedding jobs"
  ON embedding_jobs
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

-- Users can read their own embedding jobs
CREATE POLICY "Users can read their own embedding jobs"
  ON embedding_jobs
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- Users can update their own embedding jobs
CREATE POLICY "Users can update their own embedding jobs"
  ON embedding_jobs
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Users can delete their own embedding jobs
CREATE POLICY "Users can delete their own embedding jobs"
  ON embedding_jobs
  FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);
```

### Agents Table Policies

```sql
-- Enable RLS
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;

-- Users can insert their own agents
CREATE POLICY "Users can insert their own agents"
  ON agents
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

-- Users can read their own agents
CREATE POLICY "Users can read their own agents"
  ON agents
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- Users can update their own agents
CREATE POLICY "Users can update their own agents"
  ON agents
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Users can delete their own agents
CREATE POLICY "Users can delete their own agents"
  ON agents
  FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);
```

## Database Functions

### 1. `match_documents` Function

⚠️ **CRITICAL ISSUE IDENTIFIED**: This function needs to be updated to work properly with RLS and authenticated users.

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
LANGUAGE SQL STABLE
SECURITY DEFINER
AS $$
  SELECT
    documents.id,
    documents.content,
    documents.metadata,
    1 - (documents.embedding <=> query_embedding) AS similarity
  FROM documents
  WHERE 1 - (documents.embedding <=> query_embedding) > match_threshold
    AND documents.user_id = query_user_id
  ORDER BY similarity DESC
  LIMIT match_count;
$$;
```

**⚠️ POTENTIAL ISSUE**: The function uses `SECURITY DEFINER` which bypasses RLS, but it manually filters by `query_user_id`. However, if the JWT authentication is not working properly, the `query_user_id` parameter might not be correctly passed or validated.

**Alternative Implementation with RLS**:
```sql
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding VECTOR(768),
  match_threshold FLOAT,
  match_count INT
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE SQL STABLE
SECURITY INVOKER
AS $$
  SELECT
    documents.id,
    documents.content,
    documents.metadata,
    1 - (documents.embedding <=> query_embedding) AS similarity
  FROM documents
  WHERE 1 - (documents.embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
$$;
```

### 2. `update_agent_last_active` Function

```sql
CREATE OR REPLACE FUNCTION update_agent_last_active()
RETURNS TRIGGER AS $$
BEGIN
  NEW.last_active = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

## Storage Configuration

### Buckets

- **`documents`**: Stores uploaded files (PDF, DOCX, TXT, MD)
  - Public access: No
  - File size limit: 50MB
  - Allowed MIME types: `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `text/plain`, `text/markdown`

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

## Authentication Configuration

### JWT Token Requirements

**Critical JWT Claims for RLS to work**:
- `sub`: User ID (UUID) - **MUST match user_id in database**
- `aud`: Must be "authenticated" - **REQUIRED for RLS policies**
- `role`: Must be "authenticated" - **REQUIRED for RLS policies**
- `exp`: Token expiration timestamp
- `iat`: Token issued at timestamp

### Environment Variables

**Required for TxAgent Container**:
```bash
# Supabase Configuration
SUPABASE_URL=https://bfjfjxzdjhraabputkqi.supabase.co
SUPABASE_ANON_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...  # For client creation
SUPABASE_SERVICE_ROLE_KEY=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...  # For admin operations
SUPABASE_JWT_SECRET=your-jwt-secret-here  # For JWT validation
SUPABASE_STORAGE_BUCKET=documents
```

## 🚨 CRITICAL AUTHENTICATION ISSUES IDENTIFIED

### Issue 1: RLS Policy Dependency on JWT Authentication

**Problem**: RLS policies use `auth.uid()` which requires proper JWT authentication context. If the Supabase client is not properly authenticated, `auth.uid()` returns NULL, causing all RLS policies to fail.

**Current Error Pattern**: 
- JWT token validation succeeds in TxAgent
- Supabase client creation fails with `'dict' object has no attribute 'headers'`
- Database queries fail because `auth.uid()` is NULL

### Issue 2: Supabase Client Authentication Method

**Problem**: The current implementation tries to pass JWT tokens incorrectly to the Supabase client.

**Correct Implementation**:
```python
def _get_supabase_client(self, jwt: Optional[str] = None) -> Client:
    if jwt:
        client = create_client(supabase_url, supabase_key)
        # Method 1: Set session from JWT
        try:
            client.auth.set_session_from_url(f"#access_token={jwt}&token_type=bearer")
            return client
        except:
            # Method 2: Manual header setting
            client.auth._headers = {"Authorization": f"Bearer {jwt}"}
            return client
    else:
        return self.supabase
```

### Issue 3: Function Parameter Mismatch

**Problem**: The `match_documents` function expects `query_user_id` parameter, but if we use `SECURITY INVOKER` instead of `SECURITY DEFINER`, we don't need this parameter.

**Recommended Fix**:
```sql
-- Update the function to use SECURITY INVOKER and rely on RLS
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding VECTOR(768),
  match_threshold FLOAT DEFAULT 0.5,
  match_count INT DEFAULT 5
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE SQL STABLE
SECURITY INVOKER
AS $$
  SELECT
    documents.id,
    documents.content,
    documents.metadata,
    1 - (documents.embedding <=> query_embedding) AS similarity
  FROM documents
  WHERE 1 - (documents.embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
$$;
```

## 🔧 Recommended Fixes

### 1. Update Database Function
```sql
-- Drop the existing function
DROP FUNCTION IF EXISTS match_documents(VECTOR(768), FLOAT, INT, UUID);

-- Create new function without user_id parameter (relies on RLS)
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding VECTOR(768),
  match_threshold FLOAT DEFAULT 0.5,
  match_count INT DEFAULT 5
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE SQL STABLE
SECURITY INVOKER
AS $$
  SELECT
    documents.id,
    documents.content,
    documents.metadata,
    1 - (documents.embedding <=> query_embedding) AS similarity
  FROM documents
  WHERE 1 - (documents.embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
$$;
```

### 2. Update TxAgent Code
```python
# In embedder.py, update the RPC call
result = client.rpc("match_documents", {
    "query_embedding": query_embedding,
    "match_threshold": 0.5,
    "match_count": top_k
    # Remove query_user_id parameter
}).execute()
```

### 3. Test RLS Policies
```sql
-- Test if auth.uid() works properly
SELECT auth.uid();  -- Should return user UUID when authenticated

-- Test document access
SELECT COUNT(*) FROM documents;  -- Should only return user's documents
```

## 🧪 Testing Authentication

### Test JWT Token Validation
```python
# Test if JWT contains required claims
import jwt
token = "your_jwt_token_here"
payload = jwt.decode(token, options={"verify_signature": False})
print(f"User ID (sub): {payload.get('sub')}")
print(f"Audience (aud): {payload.get('aud')}")
print(f"Role: {payload.get('role')}")
```

### Test Supabase Client Authentication
```python
# Test if client is properly authenticated
client = create_client(supabase_url, supabase_key)
client.auth.set_session_from_url(f"#access_token={jwt_token}&token_type=bearer")

# Test if auth.uid() works
result = client.rpc("auth.uid").execute()
print(f"Authenticated user ID: {result.data}")
```

## 📋 Migration Required

To fix the authentication issues, run this migration:

```sql
-- Update match_documents function
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding VECTOR(768),
  match_threshold FLOAT DEFAULT 0.5,
  match_count INT DEFAULT 5
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
)
LANGUAGE SQL STABLE
SECURITY INVOKER
AS $$
  SELECT
    documents.id,
    documents.content,
    documents.metadata,
    1 - (documents.embedding <=> query_embedding) AS similarity
  FROM documents
  WHERE 1 - (documents.embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
$$;
```

## 🎯 Summary

The main issue is likely in the combination of:
1. **Incorrect Supabase client authentication** (fixed in recent updates)
2. **Database function expecting user_id parameter** when it should rely on RLS
3. **RLS policies requiring proper JWT context** which isn't being established

The recommended fix is to update the `match_documents` function to use `SECURITY INVOKER` and rely on RLS policies instead of manual user filtering.