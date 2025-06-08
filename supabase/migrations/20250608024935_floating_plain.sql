/*
  # Fix match_documents function for proper RLS integration

  1. Function Changes
    - Remove query_user_id parameter (rely on RLS instead)
    - Change from SECURITY DEFINER to SECURITY INVOKER
    - Let RLS policies handle user filtering automatically

  2. Benefits
    - Simpler function signature
    - Proper RLS integration
    - Better security model
    - Eliminates parameter mismatch issues
*/

-- Drop the existing function with the old signature
DROP FUNCTION IF EXISTS match_documents(VECTOR(768), FLOAT, INT, UUID);

-- Create new function that relies on RLS for user filtering
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

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION match_documents(VECTOR(768), FLOAT, INT) TO authenticated;