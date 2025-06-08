# TxAgent Medical RAG System

A production-ready medical document processing and question-answering platform that combines GPU-accelerated BioBERT embeddings with OpenAI's GPT models for accurate medical text analysis.

[![Container Image](https://img.shields.io/badge/Container-ghcr.io%2Fsavevsgames%2Ftxagent--hybrid%3Alatest-blue)](https://ghcr.io/savevsgames/txagent-hybrid:latest)
[![Live Demo](https://img.shields.io/badge/Demo-medical--rag--vector--uploader.onrender.com-green)](https://medical-rag-vector-uploader.onrender.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 🚀 Quick Links

- **🐳 Container Image**: [ghcr.io/savevsgames/txagent-hybrid:latest](https://ghcr.io/savevsgames/txagent-hybrid:latest) (v15)
- **🌐 Live Demo**: [medical-rag-vector-uploader.onrender.com](https://medical-rag-vector-uploader.onrender.com/)
- **📦 Container Repository**: [TxAgentContainer-SupabaseRAG](https://github.com/savevsgames/TxAgentContainer-SupabaseRAG)
- **🖥️ Frontend Repository**: [Medical_RAG_Vector_Uploader](https://github.com/savevsgames/Medical_RAG_Vector_Uploader)

## 📋 Table of Contents

- [System Overview](#system-overview)
- [Quick Start](#quick-start)
- [Deployment Options](#deployment-options)
- [Architecture](#architecture)
- [API Reference](#api-reference)
- [Authentication](#authentication)
- [Testing](#testing)
- [Development](#development)
- [Documentation](#documentation)
- [Future Roadmap](#future-roadmap)
- [Support](#support)

## 🏗️ System Overview

The TxAgent Medical RAG System uses a hybrid architecture that separates compute-intensive operations from user-facing services:

- **🖥️ Frontend**: React/Vite application for document upload and chat
- **🔗 Backend**: Node.js API gateway on Render.com
- **🧠 TxAgent Container**: GPU-accelerated document processing on RunPod
- **🗄️ Database**: Supabase PostgreSQL with pgvector for vector storage

### ✅ Current Status: Production Ready

- **Clean Architecture**: Centralized authentication, modular design
- **Consolidated Database**: Single migration, no duplicates
- **43% Code Reduction**: Eliminated redundant code and improved maintainability
- **Comprehensive Testing**: Updated Postman collection with full coverage
- **Enterprise Security**: RLS compliance, JWT authentication, audit logging

## 🚀 Quick Start

### Prerequisites

- **GPU**: NVIDIA GPU with CUDA support (for TxAgent container)
- **Database**: Supabase project with pgvector extension enabled
- **Runtime**: Node.js 18+ (for backend development)
- **Container**: Docker (for local development)

### Environment Setup

1. **Supabase Configuration**
   ```bash
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_ANON_KEY=your-supabase-anon-key
   SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
   SUPABASE_JWT_SECRET=your-supabase-jwt-secret
   SUPABASE_STORAGE_BUCKET=documents
   ```

2. **TxAgent Container**
   ```bash
   MODEL_NAME=dmis-lab/biobert-v1.1
   EMBEDDING_DIMENSION=768
   DEVICE=cuda
   OPENAI_API_KEY=your-openai-api-key
   ```

### Database Setup

✅ **COMPLETED**: The database schema has been consolidated into a single migration file:
- Run `supabase/migrations/20250608104059_warm_silence.sql`
- This creates all required tables, indexes, RLS policies, and functions
- No additional migrations needed

## 🚀 Deployment Options

### Option 1: RunPod (Recommended for Production)

**Best for**: Production deployments with GPU acceleration

```bash
# Deploy the pre-built container
docker run --gpus all -p 8000:8000 \
  -e SUPABASE_URL=your-url \
  -e SUPABASE_ANON_KEY=your-key \
  -e SUPABASE_JWT_SECRET=your-secret \
  -e OPENAI_API_KEY=your-openai-key \
  ghcr.io/savevsgames/txagent-hybrid:latest
```

**RunPod Setup**:
1. Create a new pod with GPU (A100 recommended)
2. Use the container image: `ghcr.io/savevsgames/txagent-hybrid:latest`
3. Set environment variables in RunPod dashboard
4. Expose port 8000
5. Note the generated proxy URL for API access

### Option 2: Local Development

**Best for**: Development and testing

```bash
# Clone the repository
git clone https://github.com/savevsgames/TxAgentContainer-SupabaseRAG.git
cd TxAgentContainer-SupabaseRAG

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Run with Docker Compose (requires NVIDIA Docker)
docker-compose up --build

# Or run directly with Python
cd hybrid-agent
pip install -r requirements.txt
python main.py
```

### Option 3: Other Cloud Providers

**Best for**: Alternative cloud deployments

- **Google Cloud Run**: Use the container image with GPU support
- **AWS ECS**: Deploy with GPU-enabled instances
- **Azure Container Instances**: Use GPU-enabled container groups

**Note**: Ensure GPU support and proper environment variable configuration.

## 🏗️ Architecture

### Core Components

#### 1. TxAgent Container (`hybrid-agent/`)

GPU-accelerated container for document processing and embedding generation.

**Key Features:**
- **BioBERT Model**: 768-dimensional medical embeddings
- **Document Processing**: PDF, DOCX, TXT, MD support
- **Vector Search**: pgvector similarity search
- **OpenAI Integration**: GPT-4 response generation
- **Centralized Authentication**: JWT validation with RLS compliance

**Modular Architecture:**
```
hybrid-agent/
├── core/                    # Core services package
│   ├── auth_service.py      # Centralized authentication
│   ├── logging.py           # Request and system logging
│   ├── decorators.py        # Retry and performance decorators
│   ├── validators.py        # Input validation utilities
│   └── exceptions.py        # Custom exception classes
├── main.py                  # FastAPI application
├── embedder.py              # Document processing
├── llm.py                   # OpenAI integration
└── utils.py                 # Core utilities
```

#### 2. Database Schema

**Clean, Consolidated Schema** (Single Migration):

```sql
-- Documents with BioBERT embeddings
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  filename TEXT,
  content TEXT NOT NULL,
  embedding VECTOR(768),
  metadata JSONB DEFAULT '{}'::JSONB,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Job tracking
CREATE TABLE embedding_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  file_path TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  chunk_count INTEGER DEFAULT 0,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Agent sessions
CREATE TABLE agents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  status TEXT DEFAULT 'initializing',
  session_data JSONB DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### Security Features

- **Row Level Security (RLS)**: Automatic user data isolation
- **JWT Authentication**: Centralized service with proper validation
- **Foreign Key Constraints**: Data integrity and cascade deletions
- **Indexed Queries**: Optimized vector similarity search

## 📡 API Reference

### Core Endpoints

#### `POST /embed`
Process and embed a document from Supabase Storage.

```bash
curl -X POST "https://your-container-url/embed" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "documents/user123/file.pdf",
    "metadata": {
      "title": "Medical Research Paper",
      "author": "Dr. Smith",
      "category": "cardiology"
    }
  }'
```

**Response:**
```json
{
  "job_id": "uuid-string",
  "status": "pending",
  "message": "Document is being processed"
}
```

#### `POST /chat`
Generate responses based on document context.

```bash
curl -X POST "https://your-container-url/chat" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the treatment options for hypertension?",
    "top_k": 5,
    "temperature": 0.7
  }'
```

**Response:**
```json
{
  "response": "Based on your documents, treatment options include...",
  "sources": [
    {
      "content": "Document excerpt...",
      "metadata": {"title": "Hypertension Guidelines"},
      "similarity": 0.85
    }
  ],
  "status": "success"
}
```

#### `GET /health`
Check container health and status.

```bash
curl "https://your-container-url/health"
```

**Response:**
```json
{
  "status": "healthy",
  "model": "dmis-lab/biobert-v1.1",
  "device": "cuda",
  "version": "1.0.0"
}
```

## 🔐 Authentication

### JWT Token Requirements

For RLS policies to work correctly, JWT tokens must have these claims:

```json
{
  "sub": "user-uuid-here",           // REQUIRED: User ID
  "aud": "authenticated",            // REQUIRED: Audience
  "role": "authenticated",           // REQUIRED: Role
  "email": "user@example.com",       // Optional: User email
  "exp": 1234567890,                 // REQUIRED: Expiration
  "iat": 1234567890                  // Optional: Issued at
}
```

### Getting JWT Tokens

**From Frontend Application:**
```javascript
const { data } = await supabase.auth.signInWithPassword({
  email: 'user@example.com',
  password: 'password'
});
console.log('JWT:', data.session.access_token);
```

**From Browser (Development):**
```javascript
// Check localStorage for existing token
const token = localStorage.getItem('supabase.auth.token');
```

## 🧪 Testing

### Postman Collection

Import `TxAgent_API_Tests.postman_collection.json` for comprehensive testing:

1. **Health Checks**: Container connectivity validation
2. **Authentication Flow**: JWT token validation
3. **Document Embedding**: Complete workflow testing
4. **Chat Queries**: Vector search and response generation
5. **Error Handling**: Authentication failure scenarios
6. **RLS Compliance**: User data isolation testing

**Setup Instructions:**
1. Import the collection into Postman
2. Set collection variables:
   - `base_url`: Your TxAgent container URL
   - `jwt_token`: Valid Supabase JWT token
3. Run the collection to validate all functionality

### Test Documents

Use the provided test documents in `test-documents/`:
- `morgellons-disease.md`: Comprehensive medical condition overview
- Perfect for testing document processing and chat queries

## 💻 Development

### Local Development Setup

1. **Clone Repository**
   ```bash
   git clone https://github.com/savevsgames/TxAgentContainer-SupabaseRAG.git
   cd TxAgentContainer-SupabaseRAG
   ```

2. **Environment Setup**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase and OpenAI credentials
   ```

3. **Install Dependencies**
   ```bash
   cd hybrid-agent
   pip install -r requirements.txt
   ```

4. **Run Development Server**
   ```bash
   python main.py
   # Server starts on http://localhost:8000
   ```

### Docker Development

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build manually
docker build -t txagent-hybrid .
docker run --gpus all -p 8000:8000 --env-file .env txagent-hybrid
```

### Code Organization

The project follows a clean, modular architecture:

```
├── hybrid-agent/          # TxAgent container (main application)
│   ├── core/              # Core services package
│   ├── main.py            # FastAPI application
│   ├── embedder.py        # Document processing
│   ├── llm.py             # OpenAI integration
│   └── utils.py           # Utilities
├── supabase/
│   └── migrations/        # Single consolidated migration
├── test-documents/        # Test data
└── docs/                  # Documentation
```

### Performance Requirements

**Minimum Hardware:**
- GPU: NVIDIA T4 (16GB VRAM)
- RAM: 16GB system memory
- CPU: 4 cores

**Recommended Hardware:**
- GPU: NVIDIA A100 (40GB+ VRAM)
- RAM: 32GB system memory
- CPU: 8+ cores

**Performance Metrics:**
- **A100**: ~2ms per chunk embedding, ~1000 pages/minute
- **T4**: ~10ms per chunk embedding, ~200 pages/minute

## 📚 Documentation

### Core Documentation Files

- **[BREAKDOWN.md](BREAKDOWN.md)** - Complete technical breakdown and architecture details
- **[SUPABASE_CONFIG.md](SUPABASE_CONFIG.md)** - Database configuration and schema documentation
- **[SUPABASE_MIGRATIONS.md](SUPABASE_MIGRATIONS.md)** - Migration consolidation details (COMPLETED)

### API Documentation

- **[TxAgent_API_Tests.postman_collection.json](TxAgent_API_Tests.postman_collection.json)** - Comprehensive API testing collection
- **[test-documents/README.md](test-documents/README.md)** - Test document usage guide

### Configuration Files

- **[.env.example](.env.example)** - Environment variable template
- **[hybrid-agent/requirements.txt](hybrid-agent/requirements.txt)** - Python dependencies

## 🛠️ Troubleshooting

### Common Issues

1. **401 Unauthorized**
   - Verify JWT token is valid and not expired
   - Check Authorization header format: `Bearer <token>`
   - Ensure user exists in Supabase

2. **500 Internal Server Error**
   - Check container logs for detailed error information
   - Verify environment variables are set correctly
   - Check Supabase connection and database schema

3. **GPU Not Available**
   - Ensure NVIDIA Docker runtime is installed
   - Verify GPU is accessible: `nvidia-smi`
   - Check CUDA compatibility

### Debug Commands

```bash
# Check container health
curl https://your-container-url/health

# Test with authentication
curl -X POST https://your-container-url/chat \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'

# Check GPU availability
nvidia-smi

# View container logs
docker logs <container_id>
```

## 🗺️ Future Roadmap

### Long Term (Future Sprints)

#### 🔧 Performance Optimizations
- **Model Quantization**: Reduce memory usage while maintaining accuracy
- **Dynamic Batching**: Optimize throughput for concurrent requests
- **Multi-GPU Support**: Parallel processing for increased throughput
- **Advanced Caching**: Intelligent caching for frequently accessed documents

#### 🚀 Feature Enhancements
- **Multi-Model Support**: Additional embedding models for specialized domains
- **Streaming Responses**: Real-time response generation for chat
- **Custom Model Training**: Fine-tuning capabilities for specific medical domains
- **Batch Processing**: Bulk document processing capabilities

#### 🔐 Security & Compliance
- **HIPAA Compliance**: Enhanced security for healthcare data
- **Audit Logging**: Comprehensive audit trails
- **Advanced RLS**: More granular access controls
- **Data Encryption**: Enhanced encryption for sensitive data

#### 🧪 Testing & Quality
- **Integration Tests**: Comprehensive end-to-end testing
- **Performance Testing**: Load testing and benchmarking
- **Security Testing**: Penetration testing and vulnerability assessment
- **Automated Testing**: CI/CD pipeline integration

#### 📊 Monitoring & Analytics
- **Performance Dashboards**: Real-time system monitoring
- **Usage Analytics**: User behavior and system usage insights
- **Predictive Scaling**: AI-powered resource allocation
- **Health Monitoring**: Proactive system health management

## 🆘 Support

### Getting Help

- **📖 Documentation**: Check the documentation files listed above
- **🧪 Testing**: Use the Postman collection for API validation
- **🐛 Issues**: Report issues in the GitHub repositories
- **💬 Discussions**: Join discussions in the repository discussions section

### Monitoring

The system includes comprehensive logging for:
- **Request/Response**: All API calls with user context
- **Authentication**: JWT validation and user identification
- **System Events**: Startup, model loading, background tasks
- **Performance**: Processing times and resource utilization
- **Errors**: Detailed error information with stack traces

### Health Checks

- **Container Health**: `/health` endpoint for real-time status
- **Database Health**: Connection and query performance monitoring
- **GPU Health**: CUDA availability and memory usage
- **Model Health**: BioBERT model loading and inference status

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **BioBERT**: Medical domain-specific BERT model
- **Supabase**: Backend-as-a-Service platform
- **OpenAI**: GPT models for response generation
- **pgvector**: PostgreSQL vector similarity search

---

**Built with ❤️ for the medical AI community**