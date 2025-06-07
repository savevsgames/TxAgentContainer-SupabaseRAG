/*
  # Fix RLS Policies and Function Issues

  1. RLS Policy Fixes
    - Drop and recreate all RLS policies for agents, documents, and embedding_jobs tables
    - Ensure proper auth.uid() usage for user isolation

  2. Function Fix
    - Drop existing match_documents function to avoid return type conflict
    - Recreate with proper SECURITY DEFINER for RLS compatibility

  3. Security
    - All policies use authenticated role
    - Proper user_id matching with auth.uid()
*/

-- Fix agents table RLS policies
DROP POLICY IF EXISTS "Users can insert their own agents" ON agents;
DROP POLICY IF EXISTS "Users can read their own agents" ON agents;
DROP POLICY IF EXISTS "Users can update their own agents" ON agents;
DROP POLICY IF EXISTS "Users can delete their own agents" ON agents;

CREATE POLICY "Users can insert their own agents"
  ON agents
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can read their own agents"
  ON agents
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own agents"
  ON agents
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own agents"
  ON agents
  FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- Fix documents table RLS policies
DROP POLICY IF EXISTS "Users can insert their own documents" ON documents;
DROP POLICY IF EXISTS "Users can read their own documents" ON documents;
DROP POLICY IF EXISTS "Users can update their own documents" ON documents;
DROP POLICY IF EXISTS "Users can delete their own documents" ON documents;

CREATE POLICY "Users can insert their own documents"
  ON documents
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can read their own documents"
  ON documents
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

CREATE POLICY "Users can update their own documents"
  ON documents
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own documents"
  ON documents
  FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- Add missing DELETE policy for embedding_jobs
DROP POLICY IF EXISTS "Users can delete their own embedding jobs" ON embedding_jobs;

CREATE POLICY "Users can delete their own embedding jobs"
  ON embedding_jobs
  FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);

-- Drop the existing function first to avoid return type conflict
DROP FUNCTION IF EXISTS match_documents(vector, double precision, integer, uuid);

-- Recreate the match_documents function with proper RLS support
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