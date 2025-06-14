# Document Processing Flow - TxAgent Medical RAG System

## Overview

The document processing flow handles uploading, processing, and embedding medical documents into the vector database. This is a **background processing workflow** that converts documents into searchable embeddings.

## Document Processing Architecture

### 1. Upload Flow (Frontend → Backend → Storage)

```
User Upload → Frontend → Backend API → Supabase Storage
```

**Frontend (React/Vite)**:
- User selects document file (PDF, DOCX, TXT, MD)
- File uploaded to Supabase Storage via backend API
- File stored in user-specific folder: `documents/{user_id}/filename.ext`

**Backend (Node.js on Render.com)**:
- Receives file upload request
- Validates file type and size
- Uploads to Supabase Storage with proper user isolation
- Returns file path for processing

### 2. Processing Flow (Backend → TxAgent Container)

```
Backend → TxAgent Container → Background Processing → Database Storage
```

## TxAgent Container Endpoints

### POST /process-document

**Purpose**: Process and embed a document that's already in Supabase Storage

**Request Schema**:
```json
{
  "file_path": "documents/user123/medical-paper.pdf",
  "metadata": {
    "title": "Medical Research Paper",
    "author": "Dr. Smith", 
    "category": "cardiology",
    "year": "2024",
    "source": "Medical Journal"
  }
}
```

**Headers Required**:
```
Authorization: Bearer <supabase_jwt_token>
Content-Type: application/json
```

**Response**:
```json
{
  "job_id": "uuid-string",
  "status": "pending", 
  "message": "Document is being processed in the background"
}
```

**What Happens Internally**:
1. **Authentication**: JWT token validated and user ID extracted
2. **Job Creation**: Record created in `embedding_jobs` table
3. **Background Task**: Document processing scheduled
4. **File Download**: Document downloaded from Supabase Storage
5. **Text Extraction**: Content extracted based on file type
6. **Chunking**: Text split into 512-word chunks with 50-word overlap
7. **Embedding**: BioBERT generates 768-dimensional embeddings
8. **Storage**: Chunks and embeddings stored in `documents` table
9. **Job Update**: Status updated to "completed"

### GET /embedding-jobs/{job_id}

**Purpose**: Check the status of a document processing job

**Headers Required**:
```
Authorization: Bearer <supabase_jwt_token>
```

**Response**:
```json
{
  "job_id": "uuid-string",
  "status": "completed",
  "chunk_count": 15,
  "document_ids": ["doc-id-1", "doc-id-2", "..."],
  "error": null,
  "message": "Processing completed successfully"
}
```

**Status Values**:
- `pending`: Job created, waiting for processing
- `processing`: Currently being processed
- `completed`: Successfully processed and stored
- `failed`: Processing failed (check error field)

## Database Tables

### embedding_jobs Table
```sql
CREATE TABLE embedding_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  file_path TEXT NOT NULL,                    -- Path in Supabase Storage
  status TEXT NOT NULL DEFAULT 'pending',     -- Job status
  metadata JSONB DEFAULT '{}'::JSONB,         -- Job metadata
  chunk_count INTEGER DEFAULT 0,              -- Number of chunks created
  error TEXT,                                 -- Error message if failed
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);
```

### documents Table
```sql
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  filename TEXT,                              -- Original filename
  content TEXT NOT NULL,                      -- Document chunk content
  embedding VECTOR(768),                     -- BioBERT embedding
  metadata JSONB DEFAULT '{}'::JSONB,        -- Chunk metadata
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

## Document Processing Details

### Supported File Types
- **PDF**: Text extraction using PyMuPDF (fitz)
- **DOCX**: Text extraction using python-docx
- **TXT**: Direct UTF-8 text reading
- **MD**: Markdown text reading

### Text Chunking Strategy
- **Chunk Size**: 512 words per chunk
- **Overlap**: 50 words between chunks for context preservation
- **Metadata**: Each chunk includes source file info and position

### BioBERT Embedding
- **Model**: `dmis-lab/biobert-v1.1` (medical domain-specific)
- **Dimensions**: 768-dimensional vectors
- **Hardware**: CUDA-accelerated on GPU
- **Performance**: ~2ms per chunk on A100, ~10ms on T4

## Complete Document Upload Workflow

### Step 1: Frontend Upload
```javascript
// Frontend uploads file to backend
const formData = new FormData();
formData.append('file', selectedFile);

const response = await fetch('/api/upload', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${supabaseToken}`
  },
  body: formData
});

const { filePath } = await response.json();
```

### Step 2: Backend Processing Request
```javascript
// Backend calls TxAgent container
const response = await fetch(`${TXAGENT_URL}/process-document`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${supabaseToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    file_path: filePath,
    metadata: {
      title: fileMetadata.title,
      author: fileMetadata.author,
      category: fileMetadata.category
    }
  })
});

const { job_id } = await response.json();
```

### Step 3: Status Monitoring
```javascript
// Poll for job completion
const checkStatus = async () => {
  const response = await fetch(`${TXAGENT_URL}/embedding-jobs/${job_id}`, {
    headers: {
      'Authorization': `Bearer ${supabaseToken}`
    }
  });
  
  const job = await response.json();
  
  if (job.status === 'completed') {
    console.log(`Document processed: ${job.chunk_count} chunks created`);
  } else if (job.status === 'failed') {
    console.error(`Processing failed: ${job.error}`);
  }
};
```

## Security & Authentication

### JWT Token Requirements
- **sub**: User ID (must match database user_id)
- **aud**: "authenticated" (required for RLS)
- **role**: "authenticated" (required for RLS)
- **exp**: Valid expiration time

### Row Level Security (RLS)
- All tables have RLS enabled
- Users can only access their own documents and jobs
- Automatic filtering by `auth.uid() = user_id`

## Troubleshooting

### Common Issues

1. **RLS Policy Violations**
   ```
   Error: new row violates row-level security policy
   ```
   - **Cause**: JWT token missing required claims or invalid secret
   - **Solution**: Verify `SUPABASE_JWT_SECRET` matches your project
   - **Check**: Token has `sub`, `aud: "authenticated"`, `role: "authenticated"`

2. **File Not Found**
   ```
   Error: File not found in storage
   ```
   - **Cause**: File path incorrect or file not uploaded
   - **Solution**: Verify file exists in Supabase Storage
   - **Check**: File path format: `documents/{user_id}/filename.ext`

3. **Processing Failures**
   ```
   Status: failed, Error: "No text extracted"
   ```
   - **Cause**: Corrupted file or unsupported format
   - **Solution**: Re-upload file or convert to supported format
   - **Check**: File is valid PDF, DOCX, TXT, or MD

### Debug Steps

1. **Verify JWT Token**:
   ```bash
   # Decode JWT to check claims
   echo "your_jwt_token" | base64 -d
   ```

2. **Check File in Storage**:
   ```javascript
   const { data } = await supabase.storage
     .from('documents')
     .list('user123/');
   ```

3. **Monitor Job Status**:
   ```bash
   curl -H "Authorization: Bearer <token>" \
     "https://your-container-url/embedding-jobs/job-id"
   ```

## Performance Considerations

### Processing Times
- **Small documents** (1-10 pages): 30-60 seconds
- **Medium documents** (10-50 pages): 2-5 minutes  
- **Large documents** (50+ pages): 5-15 minutes

### Optimization Tips
- **Batch uploads**: Process multiple documents sequentially
- **File size limits**: Keep files under 50MB for best performance
- **Format choice**: TXT and MD process faster than PDF/DOCX

## Integration with Chat Flow

Once documents are processed:
1. **Embeddings stored**: Document chunks available for similarity search
2. **Chat queries**: Use `/chat` endpoint to query against processed documents
3. **Source attribution**: Chat responses include source document references
4. **User isolation**: Only user's own documents are searchable

The document processing flow feeds into the chat flow by creating the vector database that enables semantic search and contextual responses.