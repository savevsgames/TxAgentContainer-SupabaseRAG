# TxAgent Hybrid Container

Medical RAG Vector Uploader with BioBERT embeddings and chat capabilities.

## Overview

This container provides a hybrid approach to medical document processing, embedding, and retrieval. It integrates with Supabase for storage and vector search, enabling both direct vector database access via Row Level Security (RLS) and backend-proxied interactions.

## Features

- BioBERT-based document embedding
- Vector storage and querying via Supabase pgvector
- Document processing for multiple formats (.pdf, .docx, .txt, .md)
- JWT authentication with Supabase
- Optional RAG chat pipeline
- FastAPI endpoints for embedding, chat, and health checking

## Prerequisites

- NVIDIA GPU with CUDA support
- Supabase project with pgvector extension enabled
- Supabase storage bucket for document storage

## Environment Variables

Copy `.env.example` to `.env` and configure:

```
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_JWT_SECRET=your-supabase-jwt-secret
SUPABASE_STORAGE_BUCKET=documents

# BioBERT Model Configuration
MODEL_NAME=dmis-lab/biobert-v1.1
EMBEDDING_DIMENSION=768
DEVICE=cuda
MAX_TOKENS=512

# FastAPI Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=False

# Container Configuration
LOG_LEVEL=INFO
CHUNK_SIZE=512
CHUNK_OVERLAP=50
```

## Build and Run

### Build Docker Image

```bash
docker build -t txagent-hybrid .
```

### Run Container

```bash
docker run --gpus all -p 8000:8000 --env-file .env txagent-hybrid
```

### Deploy to RunPod

1. Push the image to a Docker registry
2. Create a RunPod template with the image
3. Deploy on an A100 80GB GPU instance

## API Endpoints

### Embed Document

```
POST /embed
```

Request:
```json
{
  "file_path": "path/to/document.pdf",
  "metadata": {
    "title": "Medical Research Paper",
    "author": "Dr. Smith",
    "category": "oncology"
  }
}
```

### Chat

```
POST /chat
```

Request:
```json
{
  "query": "What treatments are available for lung cancer?",
  "history": [],
  "top_k": 5,
  "temperature": 0.7
}
```

### Health Check

```
GET /health
```

## Required Supabase Setup

1. Enable pgvector extension
2. Create the following tables and functions:

```sql
-- Enable pgvector extension
create extension if not exists vector;

-- Documents table with RLS
create table documents (
  id uuid primary key default gen_random_uuid(),
  content text not null,
  embedding vector(768),
  metadata jsonb default '{}'::jsonb,
  user_id uuid references auth.users(id) on delete cascade not null,
  created_at timestamp with time zone default now()
);

-- Enable RLS
alter table documents enable row level security;

-- Create policy for authenticated users to read their own documents
create policy "Users can read their own documents"
on documents for select
using (auth.uid() = user_id);

-- Create policy for authenticated users to insert their own documents
create policy "Users can insert their own documents"
on documents for insert
with check (auth.uid() = user_id);

-- Function for similarity search
create or replace function match_documents(
  query_embedding vector(768),
  match_threshold float,
  match_count int,
  query_user_id uuid
)
returns table (
  id uuid,
  content text,
  metadata jsonb,
  similarity float
)
language sql stable
as $$
  select
    documents.id,
    documents.content,
    documents.metadata,
    1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  where 1 - (documents.embedding <=> query_embedding) > match_threshold
    and documents.user_id = query_user_id
  order by similarity desc
  limit match_count;
$$;
```

## Integrating with Your Application

1. When a user uploads a document to Supabase Storage, call the `/embed` endpoint with the file path.
2. The container will process the document and store embeddings in the `documents` table.
3. For RAG queries, call the `/chat` endpoint with the user's query.
4. The container will find relevant document chunks and generate a response.

## Security Considerations

- JWT authentication is required for all endpoints
- Row Level Security ensures users can only access their own documents
- Service role key is used for administrative operations