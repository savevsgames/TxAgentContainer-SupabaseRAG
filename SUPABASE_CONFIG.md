# Supabase Database Configuration

This document provides a comprehensive overview of the Supabase database schema, policies, and functions for the Medical RAG Vector Uploader system.

## Database Overview

The system uses PostgreSQL with the `pgvector` extension for vector similarity search. All tables implement Row Level Security (RLS) to ensure users can only access their own data.

## Extensions

```sql
-- Required extensions
CREATE EXTENSION IF NOT EXISTS vector;
```

## Tables Schema

### 1. `documents` Table

Stores document chunks with their vector embeddings for similarity search.

```sql
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  content TEXT NOT NULL,
  embedding VECTOR(768),
  metadata JSONB DEFAULT '{}'::JSONB,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

**Columns:**
- `id`: Unique identifier for each document chunk
- `content`: The actual text content of the document chunk
- `embedding`: 768-dimensional vector embedding (BioBERT)
- `metadata`: JSON metadata (title, author, chunk_index, etc.)
- `user_id`: Foreign key to Supabase auth.users table
- `created_at`: Timestamp when the document was created

**Indexes:**
```sql
CREATE INDEX documents_embedding_idx ON documents
USING ivfflat (embedding vector_cosine_ops) WITH (lists='100');

CREATE INDEX documents_user_id_idx ON documents(user_id);
```

### 2. `embedding_jobs` Table

Tracks the status of document embedding jobs processed by the TxAgent container.

```sql
CREATE TABLE embedding_jobs (
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
```

**Columns:**
- `id`: Unique identifier for the embedding job
- `file_path`: Path to the file in Supabase Storage
- `status`: Job status (`pending`, `processing`, `completed`, `failed`)
- `metadata`: JSON metadata including document IDs created
- `chunk_count`: Number of document chunks created
- `error`: Error message if job failed
- `user_id`: Foreign key to Supabase auth.users table
- `created_at`: Timestamp when job was created
- `updated_at`: Timestamp when job was last updated

**Indexes:**
```sql
CREATE INDEX embedding_jobs_user_id_idx ON embedding_jobs(user_id);
CREATE INDEX embedding_jobs_status_idx ON embedding_jobs(status);
```

### 3. `agents` Table

Manages TxAgent container sessions and their status.

```sql
CREATE TABLE agents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  status TEXT DEFAULT 'initializing',
  session_data JSONB DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  last_active TIMESTAMPTZ DEFAULT now(),
  terminated_at TIMESTAMPTZ
);
```

**Columns:**
- `id`: Unique identifier for the agent session
- `user_id`: Foreign key to Supabase auth.users table
- `status`: Agent status (`initializing`, `active`, `idle`, `terminated`)
- `session_data`: JSON data including container_id, endpoint_url, capabilities
- `created_at`: Timestamp when agent session was created
- `last_active`: Timestamp of last agent activity
- `terminated_at`: Timestamp when agent was terminated

**Indexes:**
```sql
CREATE INDEX agents_user_id_idx ON agents(user_id);
CREATE INDEX agents_status_idx ON agents(status);
CREATE INDEX agents_last_active_idx ON agents(last_active);
```

**Constraints:**
```sql
ALTER TABLE agents ADD CONSTRAINT agents_status_check 
CHECK (status = ANY (ARRAY['initializing'::text, 'active'::text, 'idle'::text, 'terminated'::text]));
```

**Triggers:**
```sql
CREATE TRIGGER update_agents_last_active 
BEFORE UPDATE ON agents 
FOR EACH ROW 
EXECUTE FUNCTION update_agent_last_active();
```

## Row Level Security (RLS) Policies

All tables have RLS enabled with user-specific access policies.

### Documents Table Policies

```sql
-- Enable RLS
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- Users can insert their own documents
CREATE POLICY "Users can insert their own documents"
  ON documents
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

-- Users can read their own documents
CREATE POLICY "Users can read their own documents"
  ON documents
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- Users can update their own documents
CREATE POLICY "Users can update their own documents"
  ON documents
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Users can delete their own documents
CREATE POLICY "Users can delete their own documents"
  ON documents
  FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);
```

### Embedding Jobs Table Policies

```sql
-- Enable RLS
ALTER TABLE embedding_jobs ENABLE ROW LEVEL SECURITY;

-- Users can insert their own embedding jobs
CREATE POLICY "Users can insert their own embedding jobs"
  ON embedding_jobs
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

-- Users can read their own embedding jobs
CREATE POLICY "Users can read their own embedding jobs"
  ON embedding_jobs
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- Users can update their own embedding jobs
CREATE POLICY "Users can update their own embedding jobs"
  ON embedding_jobs
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Users can delete their own embedding jobs
CREATE POLICY "Users can delete their own embedding jobs"
  ON embedding_jobs
  FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);
```

### Agents Table Policies

```sql
-- Enable RLS
ALTER TABLE agents ENABLE ROW LEVEL SECURITY;

-- Users can insert their own agents
CREATE POLICY "Users can insert their own agents"
  ON agents
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = user_id);

-- Users can read their own agents
CREATE POLICY "Users can read their own agents"
  ON agents
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- Users can update their own agents
CREATE POLICY "Users can update their own agents"
  ON agents
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Users can delete their own agents
CREATE POLICY "Users can delete their own agents"
  ON agents
  FOR DELETE
  TO authenticated
  USING (auth.uid() = user_id);
```

## Database Functions

### 1. `match_documents` Function

Performs vector similarity search on document embeddings with user isolation.

```sql
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
```

**Parameters:**
- `query_embedding`: 768-dimensional vector to search for
- `match_threshold`: Minimum similarity threshold (0.0 to 1.0)
- `match_count`: Maximum number of results to return
- `query_user_id`: User ID for RLS filtering

**Returns:**
- `id`: Document chunk ID
- `content`: Document text content
- `metadata`: Document metadata
- `similarity`: Cosine similarity score (0.0 to 1.0)

**Usage Example:**
```sql
SELECT * FROM match_documents(
  '[0.1, 0.2, ...]'::vector(768),
  0.5,
  5,
  '496a7180-5e75-42b0-8a61-b8cf92ffe286'::uuid
);
```

### 2. `update_agent_last_active` Function

Trigger function to automatically update the `last_active` timestamp on agent updates.

```sql
CREATE OR REPLACE FUNCTION update_agent_last_active()
RETURNS TRIGGER AS $$
BEGIN
  NEW.last_active = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

## Storage Configuration

### Buckets

- **`documents`**: Stores uploaded files (PDF, DOCX, TXT, MD)
  - Public access: No
  - File size limit: 50MB
  - Allowed MIME types: `application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `text/plain`, `text/markdown`

### Storage Policies

```sql
-- Users can upload to their own folder
CREATE POLICY "Users can upload their own files"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'documents' AND auth.uid()::text = (storage.foldername(name))[1]);

-- Users can read their own files
CREATE POLICY "Users can read their own files"
ON storage.objects FOR SELECT
TO authenticated
USING (bucket_id = 'documents' AND auth.uid()::text = (storage.foldername(name))[1]);

-- Users can delete their own files
CREATE POLICY "Users can delete their own files"
ON storage.objects FOR DELETE
TO authenticated
USING (bucket_id = 'documents' AND auth.uid()::text = (storage.foldername(name))[1]);
```

## Authentication

The system uses Supabase Auth with JWT tokens. All API requests must include a valid JWT token in the Authorization header:

```
Authorization: Bearer <jwt_token>
```

### JWT Claims

Required claims in JWT tokens:
- `sub`: User ID (UUID)
- `aud`: Must be "authenticated"
- `role`: Must be "authenticated"
- `exp`: Token expiration timestamp
- `iat`: Token issued at timestamp

### User Context

The `auth.uid()` function returns the current user's ID from the JWT token, which is used in all RLS policies to ensure data isolation.

## Data Flow

### Document Upload Flow

1. User uploads file to Supabase Storage (`documents` bucket)
2. Backend extracts text and generates embeddings
3. Text chunks stored in `documents` table with user_id
4. Job status tracked in `embedding_jobs` table

### Chat Query Flow

1. User submits query via frontend
2. Backend generates query embedding
3. `match_documents` function finds similar document chunks
4. LLM generates response based on retrieved context
5. Response returned with source citations

### Agent Session Flow

1. User activates TxAgent from frontend
2. Backend creates entry in `agents` table
3. TxAgent container processes requests
4. Session data updated with container info
5. Agent terminated when user stops or times out

## Environment Variables

Required environment variables for applications using this database:

```bash
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_JWT_SECRET=your-supabase-jwt-secret

# Storage
SUPABASE_STORAGE_BUCKET=documents
```

## Migration History

1. **20250606002722_purple_bush.sql**: Initial schema setup
2. **20250606015536_empty_brook.sql**: Added embedding_jobs table
3. **20250607215243_tight_unit.sql**: Fixed RLS policies and function conflicts

## Security Considerations

1. **Row Level Security**: All tables enforce user-based data isolation
2. **JWT Validation**: All requests require valid Supabase JWT tokens
3. **SECURITY DEFINER**: The `match_documents` function uses SECURITY DEFINER to bypass RLS for vector search while maintaining user filtering
4. **Foreign Key Constraints**: Ensure data integrity with CASCADE deletes
5. **Storage Policies**: File access restricted to file owners

## Performance Considerations

1. **Vector Indexing**: IVFFlat index on embeddings for fast similarity search
2. **User ID Indexing**: Indexes on user_id columns for efficient RLS filtering
3. **Status Indexing**: Index on job status for monitoring queries
4. **Connection Pooling**: Use connection pooling for high-traffic applications

## Troubleshooting

### Common RLS Issues

- **Error**: "new row violates row-level security policy"
  - **Solution**: Ensure JWT token is valid and `auth.uid()` matches `user_id`

### Vector Search Issues

- **Error**: "function match_documents does not exist"
  - **Solution**: Run the latest migration to create the function

### Performance Issues

- **Slow similarity search**: Ensure vector index is created and statistics are updated
- **Slow user queries**: Ensure user_id indexes are present

## API Integration Examples

### Creating a Document

```javascript
const { data, error } = await supabase
  .from('documents')
  .insert({
    content: 'Document text content...',
    embedding: [0.1, 0.2, ...], // 768-dimensional array
    metadata: { title: 'Document Title', author: 'Author Name' },
    user_id: user.id
  });
```

### Similarity Search

```javascript
const { data, error } = await supabase
  .rpc('match_documents', {
    query_embedding: [0.1, 0.2, ...], // 768-dimensional array
    match_threshold: 0.5,
    match_count: 5,
    query_user_id: user.id
  });
```

### Creating an Agent Session

```javascript
const { data, error } = await supabase
  .from('agents')
  .insert({
    user_id: user.id,
    status: 'active',
    session_data: {
      container_id: 'container-123',
      endpoint_url: 'https://container.runpod.net',
      capabilities: ['embedding', 'chat']
    }
  });
```

This configuration ensures secure, scalable, and efficient operation of the Medical RAG Vector Uploader system with proper data isolation and performance optimization.