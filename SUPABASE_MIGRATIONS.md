# Supabase Migrations Consolidation

## Current Problem

The application has accumulated **15+ migration files** that are creating duplicate functions, policies, and tables. This is causing:

1. **Migration failures** due to duplicate objects
2. **Database pollution** with multiple versions of the same function
3. **RLS policy violations** indicating authentication issues
4. **Inconsistent schema state** across environments

## Migration Files Analysis

### Existing Migration Files (TO BE CONSOLIDATED)

Based on the file system, we have these migrations that need consolidation:

1. `20250606002722_purple_bush.sql` - Initial schema
2. `20250606015536_empty_brook.sql` - Additional tables
3. `20250606015501_proud_tree.sql` - Embedding jobs table (FAILED - duplicate policies)
4. `20250607214943_tiny_coral.sql` - Function updates
5. `20250607215243_tight_unit.sql` - More function updates
6. `20250608024935_floating_plain.sql` - Schema fixes
7. `20250608025354_snowy_dawn.sql` - More fixes
8. `20250608032724_foggy_wave.sql` - Function consolidation
9. `20250608043801_soft_stream.sql` - Additional fixes
10. `20250608071520_calm_heart.sql` - More consolidation
11. `20250608095733_flat_hill.sql` - Latest fixes
12. `20250608102006_noisy_lake.sql` - Current working migration

### Issues Identified

1. **Duplicate `match_documents` functions** - Multiple versions with different signatures
2. **Duplicate RLS policies** - Causing "already exists" errors
3. **Missing `filename` column** - Function expects it but table may not have it
4. **Authentication problems** - RLS policies not working with JWT tokens

## Current Database State Analysis

Based on the error logs, the current issues are:

### 1. RLS Policy Violations
```
Error: new row violates row-level security policy for table "embedding_jobs"
```

This indicates that:
- JWT tokens are not properly establishing user context
- `auth.uid()` is not returning the expected user ID
- RLS policies are blocking legitimate user operations

### 2. Function Signature Mismatches
```
Error: function public.match_documents(vector) does not exist
```

This indicates:
- Multiple function versions exist
- Code is calling wrong function signature
- Need to standardize on one function signature

### 3. Missing Database Objects
```
Error: Could not find the function public.auth.uid
```

This suggests:
- Some expected Supabase functions are not available
- Need to use alternative approaches for user identification

## Proposed Solution: Single Consolidated Migration

### Step 1: Clean Slate Migration

Create a new migration that:

1. **Drops all existing objects safely**
2. **Creates clean schema from scratch**
3. **Uses working authentication patterns**
4. **Includes proper error handling**

### Step 2: Schema Design

#### Tables

```sql
-- Core documents table
CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  filename TEXT, -- Added for compatibility
  content TEXT NOT NULL,
  embedding VECTOR(768),
  metadata JSONB DEFAULT '{}'::JSONB,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Embedding jobs tracking
CREATE TABLE IF NOT EXISTS embedding_jobs (
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

-- Agent sessions
CREATE TABLE IF NOT EXISTS agents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  status TEXT DEFAULT 'initializing',
  session_data JSONB DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  last_active TIMESTAMPTZ DEFAULT now(),
  terminated_at TIMESTAMPTZ
);
```

#### Indexes

```sql
-- Documents table indexes
CREATE INDEX IF NOT EXISTS documents_user_id_idx ON documents(user_id);
CREATE INDEX IF NOT EXISTS documents_embedding_idx ON documents 
  USING ivfflat (embedding vector_cosine_ops) WITH (lists='100');

-- Embedding jobs indexes
CREATE INDEX IF NOT EXISTS embedding_jobs_user_id_idx ON embedding_jobs(user_id);
CREATE INDEX IF NOT EXISTS embedding_jobs_status_idx ON embedding_jobs(status);

-- Agents indexes
CREATE INDEX IF NOT EXISTS agents_user_id_idx ON agents(user_id);
CREATE INDEX IF NOT EXISTS agents_status_idx ON agents(status);
CREATE INDEX IF NOT EXISTS agents_last_active_idx ON agents(last_active);
```

#### RLS Policies

```sql
-- Enable RLS on all tables
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE embedding_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;

-- Documents policies
CREATE POLICY "documents_user_isolation" ON documents
  FOR ALL TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Embedding jobs policies  
CREATE POLICY "embedding_jobs_user_isolation" ON embedding_jobs
  FOR ALL TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Agents policies
CREATE POLICY "agents_user_isolation" ON agents
  FOR ALL TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);
```

#### Functions

```sql
-- Single, standardized match_documents function
CREATE OR REPLACE FUNCTION match_documents(
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
  FROM documents d
  WHERE d.embedding IS NOT NULL
    AND d.content IS NOT NULL
    AND (1 - (d.embedding <=> query_embedding)) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$;
```

### Step 3: Authentication Fix

The main issue is that JWT authentication is not properly working with RLS. The solution:

1. **Verify JWT token format** - Ensure tokens have correct claims
2. **Test auth.uid() function** - Verify it returns user ID
3. **Alternative user identification** - Use service role for operations if needed

### Step 4: Migration Strategy

1. **Backup current data** (if any exists)
2. **Drop all existing objects** in correct order
3. **Create clean schema** with consolidated migration
4. **Test authentication flow** thoroughly
5. **Restore data** if needed

## Recommended Actions

### Immediate Steps

1. **Create consolidated migration** (`20250608120000_consolidated_schema.sql`)
2. **Remove old migration files** after successful consolidation
3. **Update application code** to use standardized function signatures
4. **Test authentication flow** end-to-end

### Testing Checklist

- [ ] JWT tokens properly validated
- [ ] RLS policies allow user operations
- [ ] `match_documents` function works with user data
- [ ] Embedding jobs can be created/updated
- [ ] Document storage and retrieval works
- [ ] Agent sessions can be managed

### Code Changes Required

1. **Update embedder.py** - Ensure it calls correct function signature
2. **Verify JWT handling** - Ensure tokens are properly passed to Supabase
3. **Test RLS policies** - Verify user isolation works correctly

## Migration File Template

```sql
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

-- [Migration content would go here]
```

This consolidation will solve the current authentication and duplication issues while providing a clean, maintainable database schema.