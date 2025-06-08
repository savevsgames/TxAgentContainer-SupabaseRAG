/*
  # Fix match_documents function for TxAgent

  1. Function Updates
    - Drop all existing match_documents functions
    - Create new function with correct signature for TxAgent
    - Ensure RLS compatibility with SECURITY INVOKER
    - Add proper grants for authenticated users

  2. Breaking Changes
    - Function signature changed to match TxAgent expectations
    - Removed manual user_id parameter (RLS handles this)
    - Updated return type to include filename field

  3. Security
    - Uses SECURITY INVOKER to respect RLS policies
    - Only authenticated users can execute the function
*/

-- Step 1: Drop ALL existing match_documents functions regardless of signature
DO $$
DECLARE
    func_record RECORD;
BEGIN
    -- Find and drop all match_documents functions
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
        EXECUTE format('DROP FUNCTION IF EXISTS %I.%I(%s) CASCADE', 
                      func_record.schema_name, 
                      func_record.proname, 
                      func_record.args);
        RAISE NOTICE 'Dropped function: %.%(%)', func_record.schema_name, func_record.proname, func_record.args;
    END LOOP;
END $$;

-- Step 2: Create the new match_documents function with correct signature
CREATE OR REPLACE FUNCTION public.match_documents(
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
    RETURN QUERY
    SELECT
        d.id,
        COALESCE(d.filename, 'Unknown') as filename,
        d.content,
        d.metadata,
        (1 - (d.embedding <=> query_embedding))::float AS similarity
    FROM
        public.documents d
    WHERE
        d.embedding IS NOT NULL 
        AND (1 - (d.embedding <=> query_embedding)) > match_threshold
    ORDER BY
        similarity DESC
    LIMIT
        match_count;
END;
$$;

-- Step 3: Grant execute permissions to authenticated users
GRANT EXECUTE ON FUNCTION public.match_documents(vector(768), float, integer) TO authenticated;

-- Step 4: Add comment explaining the function
COMMENT ON FUNCTION public.match_documents(vector(768), float, integer) IS 
'Performs vector similarity search on documents table. Uses RLS to automatically filter results by authenticated user. Returns documents ordered by similarity score.';

-- Step 5: Verify the function was created successfully
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_proc p
        JOIN pg_namespace n ON p.pronamespace = n.oid
        WHERE p.proname = 'match_documents' 
        AND n.nspname = 'public'
        AND pg_get_function_arguments(p.oid) LIKE '%vector(768)%'
    ) THEN
        RAISE NOTICE 'SUCCESS: match_documents function created successfully';
    ELSE
        RAISE EXCEPTION 'FAILED: match_documents function was not created';
    END IF;
END $$;