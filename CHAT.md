# Chat Flow - TxAgent Medical RAG System

## Overview

The chat flow enables users to ask questions about their uploaded medical documents. It uses **semantic search** to find relevant document chunks and **GPT-4** to generate contextual responses.

## Chat Architecture

### 1. Query Processing Flow

```
User Query → Embedding Generation → Vector Search → Context Retrieval → LLM Response
```

**Steps**:
1. **Query Embedding**: Convert user question to 768-dimensional BioBERT embedding
2. **Similarity Search**: Find most relevant document chunks using vector search
3. **Context Assembly**: Gather relevant chunks with metadata
4. **Response Generation**: Use OpenAI GPT-4 to generate answer based on context
5. **Source Attribution**: Return answer with source document references

### 2. Two-Endpoint Architecture

The chat flow uses **two separate endpoints** for different purposes:

#### POST /embed (Query Embedding)
- **Purpose**: Convert text to BioBERT embeddings for similarity search
- **Used by**: Companion app's chat flow
- **Authentication**: Optional (but recommended)

#### POST /chat (Complete Chat Response)
- **Purpose**: Full question-answering with context retrieval and LLM generation
- **Used by**: Direct chat interactions
- **Authentication**: Required (for document access)

## TxAgent Container Endpoints

### POST /embed

**Purpose**: Generate BioBERT embedding for text (used in chat flow)

**Request Schema**:
```json
{
  "text": "What are the symptoms of myocardial infarction?",
  "normalize": true
}
```

**Headers**:
```
Content-Type: application/json
Authorization: Bearer <jwt_token>  // Optional but recommended
```

**Response**:
```json
{
  "embedding": [0.023, 0.021, -0.008, ...],  // 768 float values
  "dimensions": 768,
  "model": "BioBERT", 
  "processing_time": 169
}
```

**Key Features**:
- **Exactly 768 dimensions**: Compatible with stored document embeddings
- **Normalized vectors**: Optional normalization for improved similarity search
- **Fast processing**: Optimized for real-time chat interactions
- **Medical domain**: BioBERT trained on medical literature

### POST /chat

**Purpose**: Complete question-answering with document context

**Request Schema**:
```json
{
  "query": "What are the treatment options for hypertension?",
  "history": [],                    // Previous conversation history
  "top_k": 5,                      // Number of similar documents to retrieve
  "temperature": 0.7,              // Response generation temperature
  "stream": false                  // Whether to stream response
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
  "response": "Based on your documents, treatment options include...",
  "sources": [
    {
      "content": "Document excerpt...",
      "metadata": {
        "title": "Hypertension Guidelines",
        "author": "Dr. Smith",
        "page": 15
      },
      "similarity": 0.85,
      "filename": "guidelines.pdf",
      "chunk_id": "chunk_123"
    }
  ],
  "processing_time": 1250,
  "model": "BioBERT",
  "tokens_used": 150,
  "status": "success"
}
```

**Status Values**:
- `success`: Answer generated with sources
- `no_results`: No relevant documents found
- `error`: Processing failed

## Chat Flow Implementation

### Option 1: Using /chat Endpoint (Direct)

**Simple Implementation**:
```javascript
const chatResponse = await fetch(`${TXAGENT_URL}/chat`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${supabaseToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    query: userQuestion,
    top_k: 5,
    temperature: 0.7
  })
});

const { response, sources } = await chatResponse.json();
```

### Option 2: Using /embed + Backend Search (Hybrid)

**Step 1: Generate Query Embedding**
```javascript
// Frontend or Backend calls TxAgent
const embedResponse = await fetch(`${TXAGENT_URL}/embed`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    text: userQuestion,
    normalize: true
  })
});

const { embedding } = await embedResponse.json();
```

**Step 2: Backend Performs Vector Search**
```javascript
// Backend calls Supabase directly
const { data: documents } = await supabase.rpc('match_documents', {
  query_embedding: embedding,
  match_threshold: 0.5,
  match_count: 5
});
```

**Step 3: Backend Calls LLM**
```javascript
// Backend generates response using OpenAI
const completion = await openai.chat.completions.create({
  model: "gpt-4-turbo-preview",
  messages: [
    {
      role: "system", 
      content: "You are a medical AI assistant."
    },
    {
      role: "user",
      content: `Context: ${documents.map(d => d.content).join('\n\n')}
      
      Question: ${userQuestion}`
    }
  ]
});
```

## Vector Similarity Search

### match_documents Function

**Database Function**:
```sql
CREATE OR REPLACE FUNCTION public.match_documents(
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
```

**Key Features**:
- **Cosine Similarity**: Uses `<=>` operator for vector distance
- **RLS Compliant**: Automatically filters by user with `SECURITY INVOKER`
- **Configurable**: Adjustable threshold and result count
- **Performance**: Uses IVFFlat index for fast search

**Usage**:
```javascript
const { data } = await supabase.rpc('match_documents', {
  query_embedding: [0.023, 0.021, ...], // 768-dimensional array
  match_threshold: 0.5,                  // Minimum similarity score
  match_count: 5                         // Number of results
});
```

## Chat Response Generation

### OpenAI Integration

**Model**: GPT-4 Turbo Preview
**Temperature**: 0.7 (configurable)
**Max Tokens**: 1000

**Prompt Structure**:
```
System: You are a medical AI assistant. Answer based on provided context.

Context:
[Document chunks with highest similarity scores]

Question: [User's question]

Answer: [Generated response]
```

### Response Enhancement

**Source Attribution**:
- Each response includes source documents
- Similarity scores for relevance ranking
- Metadata for document identification
- Chunk IDs for precise referencing

**Performance Metrics**:
- Processing time in milliseconds
- Token usage for cost tracking
- Model information for debugging

## Integration Patterns

### Pattern 1: Frontend Direct to TxAgent

```javascript
// Simple direct integration
const response = await fetch(`${TXAGENT_URL}/chat`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${supabaseToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ query: userQuestion })
});
```

**Pros**: Simple, fewer API calls
**Cons**: Exposes TxAgent URL to frontend

### Pattern 2: Backend Proxy

```javascript
// Frontend calls backend
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${supabaseToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ query: userQuestion })
});

// Backend proxies to TxAgent
app.post('/api/chat', async (req, res) => {
  const response = await fetch(`${TXAGENT_URL}/chat`, {
    method: 'POST',
    headers: {
      'Authorization': req.headers.authorization,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(req.body)
  });
  
  res.json(await response.json());
});
```

**Pros**: Hides TxAgent URL, additional security layer
**Cons**: Extra API call, more complex

### Pattern 3: Hybrid with Backend Search

```javascript
// Frontend calls backend
const response = await fetch('/api/chat', {
  method: 'POST',
  body: JSON.stringify({ query: userQuestion })
});

// Backend handles full flow
app.post('/api/chat', async (req, res) => {
  // 1. Get embedding from TxAgent
  const embedResponse = await fetch(`${TXAGENT_URL}/embed`, {
    method: 'POST',
    body: JSON.stringify({ text: req.body.query })
  });
  
  // 2. Search documents in Supabase
  const { data: documents } = await supabase.rpc('match_documents', {
    query_embedding: embedResponse.embedding
  });
  
  // 3. Generate response with OpenAI
  const completion = await openai.chat.completions.create({
    // ... OpenAI configuration
  });
  
  res.json({ response: completion.choices[0].message.content, sources: documents });
});
```

**Pros**: Full control, can customize LLM behavior
**Cons**: Most complex, requires OpenAI API key in backend

## Security & Authentication

### JWT Requirements for Chat

**Required Claims**:
```json
{
  "sub": "user-uuid",           // User ID for document filtering
  "aud": "authenticated",       // Required for RLS
  "role": "authenticated",      // Required for RLS
  "exp": 1234567890            // Valid expiration
}
```

### Row Level Security

**Automatic Filtering**:
- Vector search only returns user's documents
- No manual user filtering needed
- `auth.uid() = user_id` enforced by RLS policies

## Performance Optimization

### Embedding Cache
- Cache frequently used query embeddings
- Reduce BioBERT processing time
- Store in Redis or memory cache

### Vector Search Optimization
- **IVFFlat Index**: Fast approximate nearest neighbor search
- **Similarity Threshold**: Filter low-relevance results
- **Result Limiting**: Control response size and processing time

### Response Caching
- Cache responses for identical queries
- Use query hash as cache key
- Implement TTL for cache invalidation

## Troubleshooting

### Common Issues

1. **No Results Found**
   ```json
   {
     "response": "I couldn't find any relevant information...",
     "status": "no_results"
   }
   ```
   - **Cause**: No documents uploaded or processed
   - **Solution**: Ensure documents are successfully processed first

2. **Low Similarity Scores**
   ```json
   {
     "sources": [{"similarity": 0.3}]
   }
   ```
   - **Cause**: Query doesn't match document content well
   - **Solution**: Rephrase query or lower similarity threshold

3. **Authentication Errors**
   ```json
   {
     "detail": "Invalid token signature"
   }
   ```
   - **Cause**: JWT token invalid or expired
   - **Solution**: Refresh token or check JWT secret configuration

### Debug Steps

1. **Test Embedding Generation**:
   ```bash
   curl -X POST "${TXAGENT_URL}/embed" \
     -H "Content-Type: application/json" \
     -d '{"text": "test query"}'
   ```

2. **Test Vector Search**:
   ```javascript
   const { data } = await supabase.rpc('match_documents', {
     query_embedding: testEmbedding,
     match_threshold: 0.1,  // Lower threshold for testing
     match_count: 10
   });
   ```

3. **Check Document Count**:
   ```javascript
   const { count } = await supabase
     .from('documents')
     .select('*', { count: 'exact', head: true });
   ```

## Integration with Document Flow

**Prerequisites**:
1. Documents must be uploaded and processed via document flow
2. Embeddings must be stored in `documents` table
3. User must be authenticated with valid JWT

**Workflow**:
1. User uploads documents → Document processing flow
2. Documents embedded and stored → Vector database ready
3. User asks questions → Chat flow queries vector database
4. Relevant chunks found → Context for LLM response
5. Response generated → Answer with source attribution

The chat flow depends on the document processing flow to create the searchable knowledge base that enables intelligent question-answering.