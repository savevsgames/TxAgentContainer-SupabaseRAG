/*
  # Fix RLS Authentication Issues

  1. Database Function Updates
    - Update match_documents function to use SECURITY INVOKER and rely on RLS
    - Remove query_user_id parameter since RLS handles user filtering automatically
    - Add proper error handling and logging

  2. Agent Session Management
    - Ensure agent functions work with proper RLS context
    - Add debugging capabilities for auth.uid() testing

  3. Testing Functions
    - Add auth.uid() test function for debugging authentication context
*/

-- First, drop all existing match_documents function variations
DO $$
DECLARE
    func_record RECORD;
BEGIN
    FOR func_record IN 
        SELECT proname, oidvectortypes(proargtypes) as args
        FROM pg_proc 
        WHERE proname = 'match_documents'
    LOOP
        EXECUTE 'DROP FUNCTION IF EXISTS ' || func_record.proname || '(' || func_record.args || ') CASCADE';
        RAISE NOTICE 'Dropped function: %(%)', func_record.proname, func_record.args;
    END LOOP;
END $$;

-- Create the new match_documents function that relies on RLS
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

-- Add a test function to check auth.uid() for debugging
CREATE OR REPLACE FUNCTION test_auth_uid()
RETURNS UUID
LANGUAGE SQL STABLE
SECURITY INVOKER
AS $$
  SELECT auth.uid();
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION test_auth_uid() TO authenticated;

-- Add a function to test RLS policies
CREATE OR REPLACE FUNCTION test_user_documents_count()
RETURNS INT
LANGUAGE SQL STABLE
SECURITY INVOKER
AS $$
  SELECT COUNT(*)::INT FROM documents;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION test_user_documents_count() TO authenticated;

-- Add comments explaining the functions
COMMENT ON FUNCTION match_documents(VECTOR(768), FLOAT, INT) IS 
'Performs vector similarity search on documents table. Uses SECURITY INVOKER and RLS to automatically filter results by authenticated user. The function will only return documents that belong to the authenticated user due to RLS policies.';

COMMENT ON FUNCTION test_auth_uid() IS 
'Test function to check if auth.uid() returns the correct user ID. Used for debugging authentication issues.';

COMMENT ON FUNCTION test_user_documents_count() IS 
'Test function to count documents visible to the current user. Used for debugging RLS policies.';

-- Ensure all RLS policies are properly enabled
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE embedding_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;

-- Verify that the policies exist (this will show in the logs)
DO $$
DECLARE
    policy_count INT;
BEGIN
    SELECT COUNT(*) INTO policy_count 
    FROM pg_policies 
    WHERE tablename = 'documents' AND policyname LIKE '%Users can%';
    
    RAISE NOTICE 'Documents table has % RLS policies', policy_count;
    
    SELECT COUNT(*) INTO policy_count 
    FROM pg_policies 
    WHERE tablename = 'embedding_jobs' AND policyname LIKE '%Users can%';
    
    RAISE NOTICE 'Embedding_jobs table has % RLS policies', policy_count;
    
    SELECT COUNT(*) INTO policy_count 
    FROM pg_policies 
    WHERE tablename = 'agents' AND policyname LIKE '%Users can%';
    
    RAISE NOTICE 'Agents table has % RLS policies', policy_count;
END $$;