/*
  # Fix match_documents function signature

  This migration properly drops the existing match_documents function and recreates it
  with the correct signature to work with RLS instead of explicit user_id parameter.

  ## Changes Made
  1. Query existing function signatures to ensure proper dropping
  2. Drop all variations of the function
  3. Create new function that relies on RLS for user filtering
  4. Grant appropriate permissions
*/

-- First, let's see what functions exist and drop them all
DO $$
DECLARE
    func_record RECORD;
BEGIN
    -- Drop all variations of match_documents function
    FOR func_record IN 
        SELECT proname, oidvectortypes(proargtypes) as args
        FROM pg_proc 
        WHERE proname = 'match_documents'
    LOOP
        EXECUTE 'DROP FUNCTION IF EXISTS ' || func_record.proname || '(' || func_record.args || ') CASCADE';
        RAISE NOTICE 'Dropped function: %(%)', func_record.proname, func_record.args;
    END LOOP;
END $$;

-- Now create the new function with RLS-based user filtering
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
    (1 - (documents.embedding <=> query_embedding))::FLOAT AS similarity
  FROM documents
  WHERE (1 - (documents.embedding <=> query_embedding)) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION match_documents(VECTOR(768), FLOAT, INT) TO authenticated;

-- Grant for variations with default parameters
GRANT EXECUTE ON FUNCTION match_documents(VECTOR(768)) TO authenticated;
GRANT EXECUTE ON FUNCTION match_documents(VECTOR(768), FLOAT) TO authenticated;

-- Add comment explaining the function
COMMENT ON FUNCTION match_documents(VECTOR(768), FLOAT, INT) IS 
'Performs vector similarity search on documents table. Uses RLS to automatically filter results by authenticated user.';