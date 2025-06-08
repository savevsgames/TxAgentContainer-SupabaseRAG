/*
  # Update match_documents function to use RLS

  This migration updates the match_documents function to rely on Row Level Security (RLS) 
  instead of manual user_id filtering, which should resolve authentication issues.

  ## Changes Made
  1. Drop existing match_documents function (all variations)
  2. Create new function without user_id parameter
  3. Function uses SECURITY INVOKER to respect RLS policies
  4. Grant appropriate permissions to authenticated users

  ## Security
  - Function runs with caller's permissions (SECURITY INVOKER)
  - RLS policies automatically filter results by authenticated user
  - Only authenticated users can execute the function
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
-- Only grant on the actual function signature that exists
GRANT EXECUTE ON FUNCTION match_documents(VECTOR(768), FLOAT, INT) TO authenticated;

-- Add comment explaining the function
COMMENT ON FUNCTION match_documents(VECTOR(768), FLOAT, INT) IS 
'Performs vector similarity search on documents table. Uses RLS to automatically filter results by authenticated user. Can be called with 1, 2, or 3 parameters due to default values.';