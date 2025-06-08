/*
  # Fix match_documents function for TxAgent compatibility

  This migration fixes the match_documents function to work properly with TxAgent's
  vector similarity search requirements.

  ## Changes Made
  1. Drop all existing match_documents functions
  2. Create new function with correct signature for TxAgent
  3. Use SECURITY INVOKER to respect RLS policies
  4. Grant proper permissions to authenticated users

  ## Function Signature
  - Input: vector(768), float (threshold), integer (count)
  - Output: id, filename, content, metadata, similarity
*/

-- Step 1: Drop ALL existing match_documents functions
DO $$
DECLARE
    func_record RECORD;
    drop_sql TEXT;
BEGIN
    FOR func_record IN 
        SELECT 
            p.proname,
            pg_get_function_identity_arguments(p.oid) as args,
            n.nspname as schema_name
        FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE p.proname = 'match_documents' 
        AND n.nspname = 'public'
    LOOP
        drop_sql := format('DROP FUNCTION IF EXISTS %I.%I(%s) CASCADE', 
                          func_record.schema_name, 
                          func_record.proname, 
                          func_record.args);
        EXECUTE drop_sql;
        RAISE NOTICE 'Dropped function: %.%(%)', func_record.schema_name, func_record.proname, func_record.args;
    END LOOP;
    
    -- Also try common variations that might exist
    EXECUTE 'DROP FUNCTION IF EXISTS public.match_documents(vector, double precision, integer) CASCADE';
    EXECUTE 'DROP FUNCTION IF EXISTS public.match_documents(vector, float, integer) CASCADE';
    EXECUTE 'DROP FUNCTION IF EXISTS public.match_documents(vector, real, integer) CASCADE';
    EXECUTE 'DROP FUNCTION IF EXISTS public.match_documents(vector) CASCADE';
    EXECUTE 'DROP FUNCTION IF EXISTS public.match_documents(vector, double precision) CASCADE';
    EXECUTE 'DROP FUNCTION IF EXISTS public.match_documents(vector, float) CASCADE';
    
    RAISE NOTICE 'All match_documents functions have been dropped';
END $$;

-- Step 2: Create the new match_documents function
CREATE FUNCTION public.match_documents(
    query_embedding vector(768),
    match_threshold float DEFAULT 0.5,
    match_count integer DEFAULT 5
) RETURNS TABLE (
    id uuid,
    filename text,
    content text,
    metadata jsonb,
    similarity float
)
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
BEGIN
    -- Check if the documents table exists and has the required columns
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' AND table_name = 'documents'
    ) THEN
        RAISE EXCEPTION 'Documents table does not exist';
    END IF;

    -- Perform the similarity search
    RETURN QUERY
    SELECT
        d.id,
        COALESCE(d.filename, 'Unknown Document') as filename,
        d.content,
        COALESCE(d.metadata, '{}'::jsonb) as metadata,
        (1 - (d.embedding <=> query_embedding))::float AS similarity
    FROM
        public.documents d
    WHERE
        d.embedding IS NOT NULL 
        AND d.content IS NOT NULL
        AND (1 - (d.embedding <=> query_embedding)) > match_threshold
    ORDER BY
        similarity DESC
    LIMIT
        match_count;
END;
$$;

-- Step 3: Grant execute permissions
GRANT EXECUTE ON FUNCTION public.match_documents(vector(768), float, integer) TO authenticated;
GRANT EXECUTE ON FUNCTION public.match_documents(vector(768)) TO authenticated;
GRANT EXECUTE ON FUNCTION public.match_documents(vector(768), float) TO authenticated;

-- Step 4: Add helpful comment
COMMENT ON FUNCTION public.match_documents(vector(768), float, integer) IS 
'Performs vector similarity search on documents table using cosine similarity. 
Uses SECURITY INVOKER to respect RLS policies for user data isolation.
Returns documents ordered by similarity score (highest first).';

-- Step 5: Test the function creation (without failing the migration)
DO $$
DECLARE
    func_exists boolean := false;
BEGIN
    SELECT EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE p.proname = 'match_documents' 
        AND n.nspname = 'public'
        AND pg_get_function_arguments(p.oid) LIKE '%vector(768)%'
    ) INTO func_exists;
    
    IF func_exists THEN
        RAISE NOTICE 'SUCCESS: match_documents function created successfully with vector(768) parameter';
    ELSE
        RAISE NOTICE 'WARNING: match_documents function may not have been created properly';
    END IF;
END $$;

-- Step 6: Create a simple test function to verify vector operations work
CREATE OR REPLACE FUNCTION public.test_vector_similarity()
RETURNS float
LANGUAGE plpgsql
SECURITY INVOKER
AS $$
DECLARE
    test_vector1 vector(768);
    test_vector2 vector(768);
    similarity_score float;
BEGIN
    -- Create test vectors (all zeros and all ones for maximum difference)
    SELECT array_fill(0.0, ARRAY[768])::vector(768) INTO test_vector1;
    SELECT array_fill(1.0, ARRAY[768])::vector(768) INTO test_vector2;
    
    -- Calculate similarity
    SELECT (1 - (test_vector1 <=> test_vector2))::float INTO similarity_score;
    
    RETURN similarity_score;
END;
$$;

GRANT EXECUTE ON FUNCTION public.test_vector_similarity() TO authenticated;

COMMENT ON FUNCTION public.test_vector_similarity() IS 
'Test function to verify vector operations are working correctly. Should return a similarity score.';