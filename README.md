# TxAgent Medical RAG System

A production-ready medical document processing and question-answering platform that combines GPU-accelerated BioBERT embeddings with OpenAI's GPT models for accurate medical text analysis, enhanced with intelligent conversational health tracking capabilities.

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
- [Conversational Health Tracking](#conversational-health-tracking)
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

The TxAgent Medical RAG System uses a hybrid architecture that separates compute-intensive operations from user-facing services, enhanced with intelligent conversational health tracking:

- **🖥️ Frontend**: React/Vite application for document upload and conversational chat
- **🔗 Backend**: Node.js API gateway on Render.com
- **🧠 TxAgent Container**: GPU-accelerated document processing with conversational AI on RunPod
- **🗄️ Database**: Supabase PostgreSQL with pgvector for vector storage and health tracking

### ✅ Current Status: Production Ready with Conversational Health Tracking

- **Clean Architecture**: Centralized authentication, modular design
- **Consolidated Database**: Single migration, no duplicates
- **Conversational AI**: Natural dialogue loops for health data collection
- **Professional Bedside Manner**: "Symptom Savior" AI with healthcare professional demeanor
- **Voice-Ready**: Concise responses optimized for voice interfaces
- **Comprehensive Testing**: Updated Postman collection with full coverage
- **Enterprise Security**: RLS compliance, JWT authentication, audit logging

## 🗣️ Conversational Health Tracking

### The Core Innovation: Natural Health Data Collection

TxAgent's primary mission is **accurate health data logging through natural conversation**. The AI agent "Symptom Savior" acts as a professional triage nurse/doctor, focusing on gathering complete, accurate health records through natural dialogue.

#### Key Conversational Features

🎯 **Data Collection First**: Prioritizes accurate health records over verbose medical information  
💬 **Natural Dialogue Loops**: One question at a time, building complete entries incrementally  
🏥 **Professional Bedside Manner**: Caring healthcare professional without overwhelming verbosity  
🎤 **Voice-Optimized**: Concise responses suitable for voice interfaces  
📊 **Multi-Domain Tracking**: Symptoms, treatments, and appointments  
🔄 **Session Management**: Persistent tracking across conversation turns  

### Conversational Flow Examples

#### **Symptom Tracking Loop**
```
User: "I have a sore throat"
Symptom Savior: "I understand you're experiencing a sore throat. On a scale of 1-10, how severe is your sore throat?"

User: "About a 6"
Symptom Savior: "Got it. How long have you been experiencing this sore throat?"

User: "Since this morning"
Symptom Savior: "✅ I've successfully logged your sore throat.

**Symptom**: Sore Throat
**Severity**: 6/10
**Duration**: 8 hours

Does this look correct? You can say 'yes' to save it or tell me what to change."

User: "Yes"
Symptom Savior: "Symptom successfully saved to your health log!"
```

#### **Treatment Tracking Loop**
```
User: "I'm taking ibuprofen"
Symptom Savior: "I understand you want to track ibuprofen. What is the dosage or frequency for ibuprofen?"

User: "200mg twice a day"
Symptom Savior: "Got it. How long will you be taking ibuprofen?"

User: "For about a week"
Symptom Savior: "✅ I've successfully logged your ibuprofen.

**Treatment**: Ibuprofen
**Type**: Medication
**Dosage**: 200mg twice a day
**Duration**: For about a week

Does this look correct?"
```

#### **Professional Greeting**
```
User: "Hi"
Symptom Savior: "Hello Sarah! I'm here to help you track symptoms, medications, and appointments. How can I help you today?"
```

#### **Emergency Detection**
```
User: "I'm having severe chest pain"
Symptom Savior: "🚨 URGENT: Based on your symptoms, this may require immediate medical attention. Please contact emergency services (911) or go to the nearest emergency room immediately."
```

### Database Integration

The conversational system writes to comprehensive health tracking tables:

- **`user_symptoms`**: Complete symptom entries with severity, duration, location, triggers
- **`treatments`**: Medication and treatment tracking with dosage, duration, doctor recommendations  
- **`doctor_visits`**: Appointment scheduling and tracking with preparation notes
- **Row Level Security**: Automatic user data isolation and privacy protection

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

✅ **COMPLETED**: The database schema has been consolidated into migrations:
- Run `supabase/migrations/20250608104059_warm_silence.sql` (core tables)
- Run `supabase/migrations/20250629083320_morning_castle.sql` (health tracking)
- This creates all required tables, indexes, RLS policies, and functions

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

## 🏗️ Architecture

### Core Components

#### 1. TxAgent Container (`hybrid-agent/`)

GPU-accelerated container for document processing and conversational health tracking.

**Key Features:**
- **BioBERT Model**: 768-dimensional medical embeddings
- **Document Processing**: PDF, DOCX, TXT, MD support
- **Vector Search**: pgvector similarity search
- **OpenAI Integration**: GPT-4 response generation
- **Conversational Tracking**: Natural dialogue loops for health data collection
- **Centralized Authentication**: JWT validation with RLS compliance

**Conversational Architecture:**
```
hybrid-agent/
├── core/                    # Core services package
│   ├── auth_service.py      # Centralized authentication
│   ├── logging.py           # Request and system logging
│   └── ...                  # Other core utilities
├── main.py                  # FastAPI application with conversation routing
├── conversation_manager.py  # Strategy-based conversation management
├── symptom_tracker.py       # Symptom tracking conversational loop
├── treatment_tracker.py     # Treatment tracking conversational loop
├── appointment_tracker.py   # Appointment tracking conversational loop
├── embedder.py              # Document processing
├── llm.py                   # OpenAI integration with Symptom Savior identity
└── utils.py                 # Core utilities
```

#### 2. Database Schema

**Health Tracking Tables** (Conversational Data Collection):

```sql
-- Symptom tracking with conversational data collection
CREATE TABLE user_symptoms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  symptom_name TEXT NOT NULL,
  severity INTEGER CHECK (severity >= 1 AND severity <= 10),
  description TEXT,
  triggers TEXT[],
  duration_hours INTEGER,
  location TEXT,
  metadata JSONB DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Treatment tracking with medication management
CREATE TABLE treatments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  treatment_type TEXT NOT NULL,
  name TEXT NOT NULL,
  dosage TEXT,
  duration TEXT,
  description TEXT,
  doctor_recommended BOOLEAN DEFAULT false,
  completed BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Appointment tracking with visit management
CREATE TABLE doctor_visits (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id),
  visit_ts TIMESTAMPTZ NOT NULL,
  doctor_name TEXT,
  location TEXT,
  contact_phone TEXT,
  visit_prep TEXT,
  visit_summary TEXT,
  follow_up_required BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

**Document Storage Tables** (RAG System):

```sql
-- Documents with BioBERT embeddings
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  filename TEXT,
  content TEXT NOT NULL,
  embedding VECTOR(768),
  metadata JSONB DEFAULT '{}'::JSONB,
  user_id UUID NOT NULL REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Job tracking for document processing
CREATE TABLE embedding_jobs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  file_path TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  chunk_count INTEGER DEFAULT 0,
  user_id UUID NOT NULL REFERENCES auth.users(id),
  created_at TIMESTAMPTZ DEFAULT now()
);
```

### Security Features

- **Row Level Security (RLS)**: Automatic user data isolation for all health data
- **JWT Authentication**: Centralized service with proper validation
- **Foreign Key Constraints**: Data integrity and cascade deletions
- **Indexed Queries**: Optimized vector similarity search and health data retrieval

## 📡 API Reference

### Conversational Health Tracking Endpoints

#### `POST /chat` (Enhanced with Conversational Tracking)
Generate responses with intelligent conversational health tracking.

```bash
curl -X POST "https://your-container-url/chat" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I have a headache that started 3 hours ago, severity 7/10",
    "context": {
      "user_profile": {
        "full_name": "Sarah Johnson",
        "age": 28,
        "conditions": ["migraine"],
        "medications": ["sumatriptan"]
      },
      "conversation_history": [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello Sarah! I'\''m here to help you track symptoms, medications, and appointments. How can I help you today?"}
      ]
    },
    "tracking_session_id": null
  }'
```

**Response for Symptom Tracking:**
```json
{
  "response": "I understand you're experiencing a headache. On a scale of 1-10, how severe is your headache?",
  "sources": [],
  "processing_time": 245,
  "model": "Symptom Savior",
  "tokens_used": 0,
  "status": "success",
  "tracking_session_id": "symptom_user123_1704067200.123",
  "conversation_analysis": {
    "strategy": {
      "type": "symptom_tracking_loop",
      "confidence": 0.9
    },
    "phase": "3"
  }
}
```

**Response for Session Continuation:**
```bash
curl -X POST "https://your-container-url/chat" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "About a 7",
    "tracking_session_id": "symptom_user123_1704067200.123"
  }'
```

### Core Document Processing Endpoints

#### `POST /embed`
Generate BioBERT embeddings for text (used in chat flow).

```bash
curl -X POST "https://your-container-url/embed" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "What are the symptoms of myocardial infarction?",
    "normalize": true
  }'
```

#### `POST /process-document`
Process and embed a document from Supabase Storage.

```bash
curl -X POST "https://your-container-url/process-document" \
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

#### `GET /health`
Check container health and conversational capabilities.

```bash
curl "https://your-container-url/health"
```

**Response:**
```json
{
  "status": "healthy",
  "model": "dmis-lab/biobert-v1.1",
  "device": "cuda",
  "version": "1.3.0",
  "capabilities": {
    "conversational_loops": true,
    "symptom_tracking": true,
    "treatment_tracking": true,
    "appointment_tracking": true,
    "llm_suppression": true,
    "tracking_session_management": true,
    "improved_bedside_manner": true
  }
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

## 🧪 Testing

### Postman Collection

Import `TxAgent_API_Tests.postman_collection.json` for comprehensive testing:

1. **Health Checks**: Container connectivity and conversational capabilities
2. **Authentication Flow**: JWT token validation
3. **Conversational Tracking**: Complete symptom, treatment, and appointment loops
4. **Document Processing**: Complete workflow testing
5. **Chat Queries**: Vector search and response generation
6. **Error Handling**: Authentication failure scenarios
7. **RLS Compliance**: User data isolation testing

**Conversational Testing Examples:**
- Symptom tracking with incremental data collection
- Treatment logging with dosage and duration
- Appointment scheduling with confirmation loops
- Emergency detection and immediate response
- Professional greeting with user context

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

### Code Organization

The project follows a clean, modular architecture with conversational components:

```
├── hybrid-agent/          # TxAgent container (main application)
│   ├── core/              # Core services package
│   ├── main.py            # FastAPI application with conversation routing
│   ├── conversation_manager.py  # Strategy-based conversation management
│   ├── symptom_tracker.py       # Symptom tracking conversational loop
│   ├── treatment_tracker.py     # Treatment tracking conversational loop
│   ├── appointment_tracker.py   # Appointment tracking conversational loop
│   ├── embedder.py        # Document processing
│   ├── llm.py             # OpenAI integration with Symptom Savior identity
│   └── utils.py           # Utilities
├── supabase/
│   └── migrations/        # Database migrations (core + health tracking)
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
- **Conversational Response**: <300ms for tracking loop responses

## 📚 Documentation

### Core Documentation Files

- **[AGENT_AWARENESS.md](AGENT_AWARENESS.md)** - Complete conversational health tracking implementation
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

2. **Conversational Session Lost**
   - Check tracking_session_id is being passed correctly
   - Verify session hasn't timed out (sessions are temporary)
   - Restart conversation if session is lost

3. **Incomplete Data Collection**
   - Allow conversation to complete all required fields
   - Respond to follow-up questions for complete entries
   - Use confirmation loop before final save

### Debug Commands

```bash
# Check container health and conversational capabilities
curl https://your-container-url/health

# Test conversational symptom tracking
curl -X POST https://your-container-url/chat \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "I have a headache"}'

# Test professional greeting
curl -X POST https://your-container-url/chat \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "Hi", "context": {"user_profile": {"full_name": "Sarah"}}}'
```

## 🗺️ Future Roadmap

### Short Term (Next Sprint)

#### 🎤 Real-Time Voice Integration
- **Voice Interface**: Real-time audio processing using existing conversational logic
- **Speech Recognition**: High-accuracy medical term transcription
- **Voice Synthesis**: Natural speech generation for Symptom Savior responses
- **Seamless Transition**: Switch between voice and text modalities

#### 📊 Enhanced Analytics
- **Health Trends**: Pattern analysis across symptoms, treatments, and appointments
- **Predictive Insights**: Early warning systems based on symptom patterns
- **Progress Tracking**: Treatment effectiveness and appointment follow-up
- **Export Capabilities**: Comprehensive health reports for healthcare providers

### Medium Term (Future Sprints)

#### 🔧 Advanced Conversational Features
- **Multi-Language Support**: Conversational health tracking in multiple languages
- **Emotional Intelligence**: Sentiment analysis and empathetic responses
- **Personalization**: Learning user preferences and communication styles
- **Complex Scenarios**: Multi-symptom tracking and treatment interactions

#### 🏥 Healthcare Integration
- **EHR Integration**: Direct integration with electronic health records
- **Provider Portals**: Healthcare provider access to patient tracking data
- **Appointment Scheduling**: Direct integration with healthcare provider systems
- **Medication Reminders**: Intelligent medication adherence tracking

### Long Term (Future Quarters)

#### 🔐 Advanced Security & Compliance
- **HIPAA Compliance**: Enhanced security for healthcare data
- **Advanced Audit**: Comprehensive audit trails for all health interactions
- **Data Governance**: Advanced data retention and privacy controls
- **Regulatory Compliance**: Support for international healthcare regulations

#### 🧠 AI Enhancement
- **Predictive Health**: AI-powered health risk assessment
- **Clinical Decision Support**: Advanced medical guidance integration
- **Research Integration**: Connection to latest medical research and guidelines
- **Personalized Medicine**: Tailored recommendations based on individual health profiles

## 🆘 Support

### Getting Help

- **📖 Documentation**: Check the documentation files listed above
- **🧪 Testing**: Use the Postman collection for API validation
- **🐛 Issues**: Report issues in the GitHub repositories
- **💬 Discussions**: Join discussions in the repository discussions section

### Monitoring

The system includes comprehensive logging for:
- **Conversational Tracking**: Complete tracking session logs and progress
- **Health Data Operations**: All symptom, treatment, and appointment operations
- **Request/Response**: All API calls with user context
- **Authentication**: JWT validation and user identification
- **System Events**: Startup, model loading, background tasks
- **Performance**: Processing times and resource utilization
- **Errors**: Detailed error information with stack traces

### Health Checks

- **Container Health**: `/health` endpoint for real-time status
- **Conversational Capabilities**: Real-time tracking of conversational features
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

*Featuring intelligent conversational health tracking with professional bedside manner, natural dialogue loops for accurate data collection, and a carefully designed system optimized for both text and voice interfaces. "Symptom Savior" provides the caring, professional healthcare interaction users expect while maintaining focus on accurate health data collection.*