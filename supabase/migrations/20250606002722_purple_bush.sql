/*
  # Initial Schema Setup for TxAgent

  1. New Tables
     - `documents` - Stores document chunks with embeddings
     - `embedding_jobs` - Tracks document embedding jobs

  2. Indexes
     - Create index on embeddings for vector similarity search
     - Create index on user_id for faster filtering

  3. Security
     - Enable RLS for all tables
     - Create policies for user data access
*/

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content TEXT NOT NULL,
  embedding VECTOR(768),
  metadata JSONB DEFAULT '{}'::JSONB,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS documents_embedding_idx ON documents
USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);

-- Create index for user_id
CREATE INDEX IF NOT EXISTS documents_user_id_idx ON documents(user_id);

-- Embedding jobs table
CREATE TABLE IF NOT EXISTS embedding_jobs (
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

-- Create index for user_id on embedding_jobs
CREATE INDEX IF NOT EXISTS embedding_jobs_user_id_idx ON embedding_jobs(user_id);

-- Enable Row Level Security
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE embedding_jobs ENABLE ROW LEVEL SECURITY;

-- Create policies for documents
CREATE POLICY "Users can read their own documents"
ON documents FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own documents"
ON documents FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Create policies for embedding_jobs
CREATE POLICY "Users can read their own embedding jobs"
ON embedding_jobs FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own embedding jobs"
ON embedding_jobs FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own embedding jobs"
ON embedding_jobs FOR UPDATE
USING (auth.uid() = user_id);

-- Function for similarity search
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