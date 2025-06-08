/*
  # Fix match_documents function for proper RLS integration

  1. Changes Made
    - Drop existing function with correct signature (using double precision instead of float)
    - Create new function that relies on RLS for user filtering
    - Remove manual user_id parameter since RLS handles user isolation
    - Change from SECURITY DEFINER to SECURITY INVOKER to respect RLS policies
    - Add proper grants for authenticated users

  2. Security
    - Function now respects RLS policies automatically
    - No manual user filtering needed
    - Authenticated users can only see their own documents via RLS

  3. Breaking Changes
    - Function signature changed: removed query_user_id parameter
    - Calling code must be updated to not pass user_id parameter
*/

-- Drop the existing function with the correct signature
-- PostgreSQL uses 'double precision' internally for FLOAT type
DROP FUNCTION IF EXISTS match_documents(VECTOR(768), double precision, integer, UUID);

-- Also try dropping with FLOAT in case it was created that way
DROP FUNCTION IF EXISTS match_documents(VECTOR(768), FLOAT, INT, UUID);

-- Create new function that relies on RLS for user filtering
CREATE OR REPLACE FUNCTION match_documents(
  query_embedding VECTOR(768),
  match_threshold double precision DEFAULT 0.5,
  match_count integer DEFAULT 5
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  metadata JSONB,
  similarity double precision
)
LANGUAGE SQL STABLE
SECURITY INVOKER
AS $$
  SELECT
    documents.id,
    documents.content,
    documents.metadata,
    (1 - (documents.embedding <=> query_embedding))::double precision AS similarity
  FROM documents
  WHERE (1 - (documents.embedding <=> query_embedding)) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION match_documents(VECTOR(768), double precision, integer) TO authenticated;

-- Also grant with default parameters
GRANT EXECUTE ON FUNCTION match_documents(VECTOR(768)) TO authenticated;
GRANT EXECUTE ON FUNCTION match_documents(VECTOR(768), double precision) TO authenticated;