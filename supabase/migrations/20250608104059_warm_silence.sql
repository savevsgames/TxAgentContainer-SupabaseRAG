/*
# Consolidated TxAgent Schema Migration

This migration consolidates all previous migrations into a single, clean schema.
It replaces all previous migration files and creates a working database schema.

## Changes Made:
1. Dropped all existing duplicate functions and policies
2. Created clean table schema with proper RLS
3. Added standardized match_documents function
4. Fixed authentication and user isolation issues

## Tables Created:
- documents: Store document content and embeddings
- embedding_jobs: Track document processing jobs  
- agents: Manage agent sessions

## Security:
- Row Level Security enabled on all tables
- User isolation via auth.uid() policies
- Proper indexes for performance
*/

-- Step 1: Drop existing objects safely
DROP FUNCTION IF EXISTS public.match_documents(VECTOR, FLOAT, INTEGER);
DROP TABLE IF EXISTS public.documents CASCADE;
DROP TABLE IF EXISTS public.embedding_jobs CASCADE;
DROP TABLE IF EXISTS public.agents CASCADE;

-- Step 2: Create clean schema from scratch
CREATE TABLE IF NOT EXISTS public.documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  filename TEXT,
  content TEXT NOT NULL,
  embedding VECTOR(768),
  metadata JSONB DEFAULT '{}'::JSONB,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.embedding_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  file_path TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  metadata JSONB DEFAULT '{}'::JSONB,
  chunk_count INTEGER DEFAULT 0,
  error TEXT,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.agents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  status TEXT DEFAULT 'initializing',
  session_data JSONB DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  last_active TIMESTAMPTZ DEFAULT now(),
  terminated_at TIMESTAMPTZ
);

-- Step 3: Create indexes
CREATE INDEX IF NOT EXISTS documents_user_id_idx ON public.documents(user_id);
CREATE INDEX IF NOT EXISTS documents_embedding_idx ON public.documents 
  USING ivfflat (embedding vector_cosine_ops) WITH (lists='100');

CREATE INDEX IF NOT EXISTS embedding_jobs_user_id_idx ON public.embedding_jobs(user_id);
CREATE INDEX IF NOT EXISTS embedding_jobs_status_idx ON public.embedding_jobs(status);

CREATE INDEX IF NOT EXISTS agents_user_id_idx ON public.agents(user_id);
CREATE INDEX IF NOT EXISTS agents_status_idx ON public.agents(status);
CREATE INDEX IF NOT EXISTS agents_last_active_idx ON public.agents(last_active);

-- Step 4: Enable RLS on all tables
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.embedding_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agents ENABLE ROW LEVEL SECURITY;

-- Step 5: Create RLS policies
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

-- Step 6: Create standardized match_documents function
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

-- Step 7: Grant execute permission to authenticated users for the new function signature
GRANT EXECUTE ON FUNCTION public.match_documents(VECTOR(768), FLOAT, INTEGER) TO authenticated;