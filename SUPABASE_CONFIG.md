# Supabase Database Configuration

This document provides a comprehensive overview of the Supabase database schema, policies, and functions for the Medical RAG Vector Uploader system.

## Current Status: MIGRATION CONSOLIDATION NEEDED

⚠️ **CRITICAL**: The database currently has **15+ migration files** creating duplicate objects and causing failures. See `SUPABASE_MIGRATIONS.md` for consolidation plan.

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
  filename TEXT, -- Added for compatibility with match_documents function
  content TEXT NOT NULL,
  embedding VECTOR(768),
  metadata JSONB DEFAULT '{}'::JSONB,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

**Columns:**
- `id`: Unique identifier for each document chunk
- `filename`: Original filename (for function compatibility)
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

### Current RLS Implementation

```sql
-- Enable RLS on all tables
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE embedding_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;

-- Simplified user isolation policies
CREATE POLICY "documents_user_isolation" ON documents
  FOR ALL TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "embedding_jobs_user_isolation" ON embedding_jobs
  FOR ALL TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "agents_user_isolation" ON agents
  FOR ALL TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);
```

## Database Functions

### 1. `match_documents` Function

**Current Working Version** (from latest migration):

```sql
CREATE OR REPLACE FUNCTION match_documents(
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
    COALESCE(d.filename, 'Unknown Document') as filename,
    d.content,
    COALESCE(d.metadata, '{}'::jsonb) as metadata,
    (1 - (d.embedding <=> query_embedding))::float AS similarity
  FROM documents d
  WHERE d.embedding IS NOT NULL 
    AND d.content IS NOT NULL
    AND d.content != ''
    AND (1 - (d.embedding <=> query_embedding)) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$;
```

**Key Features**:
- Uses `SECURITY INVOKER` to respect RLS policies
- Returns documents filtered by user automatically
- Includes filename for compatibility
- Validates input parameters
- Optimized for performance

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

## 🚨 CURRENT CRITICAL ISSUES

### Issue 1: RLS Policy Violations

**Problem**: Embed requests are failing with RLS policy violations:
```
Error: new row violates row-level security policy for table "embedding_jobs"
```

**Root Cause**: JWT authentication is not properly establishing user context for RLS policies.

**Status**: Partially resolved in `embedder.py` by simplifying authentication flow.

### Issue 2: Multiple Migration Files

**Problem**: 15+ migration files creating duplicate objects:
- Multiple `match_documents` functions with different signatures
- Duplicate RLS policies causing "already exists" errors
- Inconsistent schema state

**Status**: Requires migration consolidation (see `SUPABASE_MIGRATIONS.md`).

### Issue 3: Function Signature Mismatches

**Problem**: Code calling wrong function signatures:
```
Error: function public.match_documents(vector) does not exist
```

**Status**: Latest migration standardizes on single function signature.

## 🔧 RECOMMENDED IMMEDIATE FIXES

### 1. Consolidate Migrations
- Create single consolidated migration
- Drop all existing duplicate objects
- Recreate clean schema

### 2. Test Authentication Flow
```sql
-- Test if auth.uid() works properly
SELECT auth.uid();  -- Should return user UUID when authenticated

-- Test document access
SELECT COUNT(*) FROM documents;  -- Should only return user's documents
```

### 3. Verify Function Signature
```sql
-- Check current function signature
SELECT 
  p.proname,
  pg_get_function_arguments(p.oid) as args
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE p.proname = 'match_documents' 
AND n.nspname = 'public';
```

### 4. Update Application Code
Ensure `embedder.py` calls the correct function signature:
```python
result = client.rpc("match_documents", {
    "query_embedding": query_embedding,
    "match_threshold": 0.5,
    "match_count": top_k
}).execute()
```

## 📋 MIGRATION CONSOLIDATION PLAN

See `SUPABASE_MIGRATIONS.md` for detailed consolidation plan including:

1. **Analysis of all existing migrations**
2. **Identification of duplicate objects**
3. **Clean schema design**
4. **Single consolidated migration file**
5. **Testing and validation procedures**

## 🎯 SUMMARY

The main issues are:
1. **Authentication**: JWT tokens not properly establishing user context for RLS
2. **Migrations**: Multiple duplicate objects causing conflicts
3. **Functions**: Inconsistent function signatures across migrations

The solution is to consolidate all migrations into a single, clean migration that creates a working schema with proper authentication and user isolation.