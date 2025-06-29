# TxAgent Medical RAG System

A production-ready medical document processing and question-answering platform that combines GPU-accelerated BioBERT embeddings with OpenAI's GPT models for accurate medical text analysis, enhanced with intelligent conversation management and natural symptom tracking capabilities.

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
- [Agent Capabilities](#agent-capabilities)
- [Agent Tools & Extensions](#agent-tools--extensions)
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

### ✅ Current Status: Production Ready with Enhanced Intelligence

- **Clean Architecture**: Centralized authentication, modular design
- **Consolidated Database**: Single migration, no duplicates
- **43% Code Reduction**: Eliminated redundant code and improved maintainability
- **Comprehensive Testing**: Updated Postman collection with full coverage
- **Enterprise Security**: RLS compliance, JWT authentication, audit logging
- **Enhanced Conversation Flow**: Phase 2.8 with improved bedside manner

## 🤖 Agent Capabilities

### Core Intelligence Features

#### 🧠 **Advanced Natural Language Processing**
- **BioBERT Integration**: Medical domain-specific language understanding
- **Contextual Symptom Extraction**: Automatically identifies symptoms, severity, duration, location, and triggers
- **Temporal Pattern Recognition**: Understands frequency, onset timing, and duration patterns
- **Quality Descriptor Analysis**: Extracts pain types, textures, and movement characteristics
- **Multi-turn Conversation Memory**: Maintains context across conversation turns

#### 💬 **Enhanced Conversation Management (Phase 2.8)**
- **Improved Bedside Manner**: Natural, professional interactions without over-eager symptom logging
- **Conversation Strategy Detection**: Distinguishes between casual chat, medical questions, and symptom logging
- **Context-Aware Responses**: Adapts response style based on conversation type and user intent
- **Emergency Detection**: Real-time identification of critical symptoms requiring immediate attention
- **Follow-up Intelligence**: Generates appropriate questions for missing symptom details

#### 📊 **Intelligent Symptom Tracking**
- **Automatic Symptom Logging**: Extracts and stores symptom data when appropriate
- **Pattern Analysis**: Identifies trends, triggers, and frequency patterns
- **Severity Assessment**: Understands numeric scales and qualitative descriptors
- **Historical Context**: Connects current symptoms with past entries
- **Medical Advice Integration**: Provides contextual health guidance with proper disclaimers

#### 🔍 **Document Intelligence**
- **Multi-format Processing**: PDF, DOCX, TXT, MD document support
- **Semantic Search**: Vector similarity search across medical documents
- **Source Attribution**: Tracks and cites relevant document sections
- **Context Integration**: Combines document knowledge with conversation context

### Conversation Flow Examples

#### **Natural Greeting Handling**
```
User: "Hi, how are you?"
TxAgent: "Hello! I'm here to help you with any health-related questions or to assist with tracking your symptoms. How can I help you today?"
```
*No aggressive symptom logging, natural conversation flow*

#### **General Health Questions**
```
User: "What's the difference between a cold and flu?"
TxAgent: "Great question! Colds and flu are both respiratory illnesses, but they're caused by different viruses...
[Provides educational information]
Are you experiencing any symptoms yourself, or is this just general information you're looking for?"
```
*Educational response with gentle inquiry*

#### **Clear Symptom Logging Intent**
```
User: "I want to log a headache I've had for 3 hours, it's about a 7/10"
TxAgent: "✅ I've logged your headache with the details you provided:
- Duration: 3 hours
- Severity: 7/10

For headaches at this severity level, rest, hydration, and a quiet environment can help..."
```
*Appropriate action with medical guidance*

#### **Emergency Detection**
```
User: "I'm having severe chest pain and can't breathe properly"
TxAgent: "🚨 URGENT: Based on your symptoms, this may require immediate medical attention. Please contact emergency services (911) or go to the nearest emergency room immediately."
```
*Immediate escalation for critical symptoms*

## 🛠️ Agent Tools & Extensions

### Current Tool Set (Minimal but Effective)

Our TxAgent implementation uses a carefully selected minimal tool set optimized for medical applications:

#### **1. Symptom Management Tools**
- **`save_symptom`**: Logs symptom data with validation and RLS compliance
- **`get_symptoms`**: Retrieves user symptom history with filtering options
- **`symptom_summary`**: Generates pattern analysis and trend insights

**Why These Tools:**
- **Medical Focus**: Specifically designed for healthcare symptom tracking
- **Privacy Compliant**: Built-in RLS ensures user data isolation
- **Contextual**: Integrates seamlessly with conversation flow
- **Validated**: Comprehensive input validation and error handling

#### **2. Document Processing Tools**
- **`process_document`**: Handles medical document embedding and storage
- **`similarity_search`**: Performs vector-based document retrieval
- **`embedding_generation`**: Creates BioBERT embeddings for medical text

**Why These Tools:**
- **Medical Domain Optimized**: BioBERT specifically trained on medical literature
- **Scalable**: Handles large document collections efficiently
- **Secure**: User-isolated document storage and retrieval

### Alternative Tool Frameworks Considered

#### **LangChain Tools**
```python
# Example of what we could have used
from langchain.tools import Tool, DuckDuckGoSearchRun
from langchain.tools.file_management import WriteFileTool
from langchain.tools.python.tool import PythonREPLTool

tools = [
    DuckDuckGoSearchRun(),
    WriteFileTool(),
    PythonREPLTool(),
    # ... many more
]
```

**Why We Didn't Choose This:**
- **Too Generic**: Not optimized for medical use cases
- **Security Concerns**: File system access and code execution risks
- **Complexity**: Overhead for our specific medical domain needs
- **Privacy**: External search tools could leak patient information

#### **OpenAI Function Calling**
```python
# Example OpenAI function definitions
functions = [
    {
        "name": "get_weather",
        "description": "Get weather information",
        "parameters": {...}
    },
    {
        "name": "send_email",
        "description": "Send an email",
        "parameters": {...}
    }
]
```

**Why We Chose a Custom Approach:**
- **Medical Specificity**: Our tools are purpose-built for healthcare
- **Data Control**: Complete control over data flow and storage
- **Compliance**: HIPAA-ready with proper audit trails
- **Integration**: Seamless integration with our existing architecture

### Potential Tool Extensions

#### **🔬 Advanced Medical Tools**

##### **Drug Interaction Checker**
```python
class DrugInteractionTool:
    """Check for drug interactions and contraindications"""
    
    def check_interactions(self, medications: List[str], new_drug: str) -> Dict:
        # Integration with medical databases
        # FDA drug interaction APIs
        # Clinical decision support systems
        pass
```

**Benefits:**
- Real-time medication safety checking
- Integration with user medication profiles
- Clinical decision support

##### **Lab Results Interpreter**
```python
class LabResultsTool:
    """Interpret and explain laboratory results"""
    
    def interpret_results(self, lab_data: Dict, reference_ranges: Dict) -> Dict:
        # Automated lab result interpretation
        # Trend analysis over time
        # Clinical significance assessment
        pass
```

**Benefits:**
- Automated lab result explanations
- Trend analysis and alerts
- Integration with symptom tracking

##### **Clinical Guidelines Tool**
```python
class ClinicalGuidelinesTool:
    """Access and apply clinical practice guidelines"""
    
    def get_guidelines(self, condition: str, symptoms: List[str]) -> Dict:
        # Access to medical guidelines databases
        # Evidence-based recommendations
        # Treatment pathway suggestions
        pass
```

**Benefits:**
- Evidence-based medical recommendations
- Up-to-date clinical guidelines
- Personalized treatment suggestions

#### **📱 Integration Tools**

##### **Wearable Data Integration**
```python
class WearableDataTool:
    """Integrate data from fitness trackers and health devices"""
    
    def sync_health_data(self, user_id: str, device_type: str) -> Dict:
        # Apple Health integration
        # Fitbit API connection
        # Continuous glucose monitors
        # Blood pressure monitors
        pass
```

**Benefits:**
- Objective health data correlation
- Continuous monitoring integration
- Automated symptom pattern detection

##### **Appointment Scheduling**
```python
class AppointmentTool:
    """Schedule and manage medical appointments"""
    
    def schedule_appointment(self, provider: str, urgency: str, symptoms: List[str]) -> Dict:
        # Healthcare provider API integration
        # Urgency-based scheduling
        # Symptom-appropriate specialist matching
        pass
```

**Benefits:**
- Automated appointment booking
- Urgency-based prioritization
- Specialist matching based on symptoms

#### **🔍 Research & Analysis Tools**

##### **Medical Literature Search**
```python
class MedicalResearchTool:
    """Search and analyze medical literature"""
    
    def search_literature(self, query: str, filters: Dict) -> List[Dict]:
        # PubMed API integration
        # Clinical trial databases
        # Medical journal access
        pass
```

**Benefits:**
- Access to latest medical research
- Evidence-based information retrieval
- Clinical trial matching

##### **Symptom Prediction Model**
```python
class SymptomPredictionTool:
    """Predict potential health issues based on symptom patterns"""
    
    def predict_conditions(self, symptom_history: List[Dict], user_profile: Dict) -> Dict:
        # Machine learning models
        # Pattern recognition
        # Risk assessment algorithms
        pass
```

**Benefits:**
- Early warning systems
- Preventive care recommendations
- Risk stratification

#### **🏥 Healthcare System Integration**

##### **Electronic Health Records (EHR)**
```python
class EHRIntegrationTool:
    """Integrate with healthcare provider EHR systems"""
    
    def sync_medical_records(self, user_id: str, provider_id: str) -> Dict:
        # FHIR standard compliance
        # HL7 message processing
        # Secure health information exchange
        pass
```

**Benefits:**
- Complete medical history access
- Provider communication
- Continuity of care

##### **Pharmacy Integration**
```python
class PharmacyTool:
    """Connect with pharmacy systems for medication management"""
    
    def check_prescription_status(self, user_id: str, medication: str) -> Dict:
        # Pharmacy API integration
        # Prescription tracking
        # Medication adherence monitoring
        pass
```

**Benefits:**
- Medication adherence tracking
- Prescription management
- Drug availability checking

### Implementation Considerations

#### **Security & Privacy**
- **HIPAA Compliance**: All tools must meet healthcare privacy standards
- **Data Encryption**: End-to-end encryption for sensitive health data
- **Audit Trails**: Comprehensive logging for all tool interactions
- **Access Controls**: Role-based permissions for different tool capabilities

#### **Integration Complexity**
- **API Management**: Handling multiple external service integrations
- **Rate Limiting**: Managing API quotas and usage limits
- **Error Handling**: Graceful degradation when external services fail
- **Data Synchronization**: Keeping multiple data sources in sync

#### **Cost Considerations**
- **API Costs**: External service usage fees
- **Compute Resources**: Additional processing requirements
- **Storage**: Increased data storage needs
- **Maintenance**: Ongoing tool maintenance and updates

### Recommended Next Tools

Based on user feedback and medical use cases, we recommend implementing these tools next:

1. **🥇 Drug Interaction Checker** - High impact, moderate complexity
2. **🥈 Wearable Data Integration** - High user value, moderate complexity  
3. **🥉 Lab Results Interpreter** - High medical value, high complexity
4. **🏅 Appointment Scheduling** - High convenience, low complexity

### Tool Development Framework

For future tool development, we've established a framework that ensures:

#### **Consistency**
```python
class BaseMedicalTool:
    """Base class for all medical tools"""
    
    def __init__(self):
        self.auth_required = True
        self.audit_logging = True
        self.rls_compliant = True
    
    def validate_input(self, data: Dict) -> bool:
        """Validate tool input data"""
        pass
    
    def execute(self, data: Dict, user_context: Dict) -> Dict:
        """Execute tool with proper logging and error handling"""
        pass
    
    def log_usage(self, user_id: str, action: str, result: Dict):
        """Log tool usage for audit and analytics"""
        pass
```

#### **Quality Standards**
- **Medical Accuracy**: All tools must provide medically accurate information
- **User Safety**: Built-in safeguards to prevent harmful recommendations
- **Professional Standards**: Adherence to medical professional guidelines
- **Continuous Validation**: Regular testing and validation of tool outputs

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
- **Enhanced Conversation Management**: Phase 2.8 with improved bedside manner

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
├── conversation_manager.py  # Enhanced conversation flow
├── nlp_processor.py         # Advanced NLP processing
├── intent_recognition.py    # Intent detection
├── agent_actions.py         # Symptom management tools
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

-- Symptom tracking
CREATE TABLE user_symptoms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  symptom_name TEXT NOT NULL,
  severity INTEGER CHECK (severity >= 1 AND severity <= 10),
  description TEXT,
  triggers TEXT[],
  duration_hours INTEGER,
  location TEXT,
  metadata JSONB DEFAULT '{}'::JSONB,
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

**Response:**
```json
{
  "embedding": [0.1234, -0.5678, ...],
  "dimensions": 768,
  "model": "BioBERT",
  "processing_time": 45
}
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

**Response:**
```json
{
  "job_id": "uuid-string",
  "status": "pending",
  "message": "Document is being processed"
}
```

#### `POST /chat`
Generate responses with enhanced conversation management.

```bash
curl -X POST "https://your-container-url/chat" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I have a headache that started 3 hours ago, severity 7/10",
    "context": {
      "user_profile": {
        "age": 28,
        "conditions": ["migraine"],
        "medications": ["sumatriptan"]
      },
      "conversation_history": [
        {"role": "user", "content": "Hi, I need help tracking symptoms"},
        {"role": "assistant", "content": "I can help you track your symptoms. What are you experiencing?"}
      ]
    },
    "top_k": 5,
    "temperature": 0.7
  }'
```

**Response:**
```json
{
  "response": "✅ I've logged your headache with the details you provided...",
  "sources": [...],
  "processing_time": 1250,
  "agent_action": {
    "action": "symptom_logged",
    "success": true,
    "data": {...}
  },
  "conversation_analysis": {
    "strategy": {"type": "symptom_logging", "confidence": 0.9},
    "phase": "2.8"
  }
}
```

#### Agent Action Endpoints

##### `POST /agent-action/save-symptom`
Directly save symptom data.

```bash
curl -X POST "https://your-container-url/agent-action/save-symptom" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "symptom_data": {
      "symptom_name": "headache",
      "severity": 7,
      "duration_hours": 3,
      "location": "forehead",
      "triggers": ["stress", "lack of sleep"]
    }
  }'
```

##### `GET /agent-action/get-symptoms`
Retrieve symptom history with filtering.

```bash
curl "https://your-container-url/agent-action/get-symptoms?limit=10&symptom_name=headache&days_back=30" \
  -H "Authorization: Bearer <jwt_token>"
```

##### `GET /agent-action/symptom-summary`
Get symptom pattern analysis.

```bash
curl "https://your-container-url/agent-action/symptom-summary?days_back=30" \
  -H "Authorization: Bearer <jwt_token>"
```

#### `GET /health`
Check container health and capabilities.

```bash
curl "https://your-container-url/health"
```

**Response:**
```json
{
  "status": "healthy",
  "model": "dmis-lab/biobert-v1.1",
  "device": "cuda",
  "version": "1.2.8",
  "capabilities": {
    "phase2_8_enhanced_conversation": true,
    "improved_bedside_manner": true,
    "advanced_nlp": true,
    "conversation_management": true,
    "symptom_tracking": true,
    "emergency_detection": true
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
5. **Enhanced Conversation Flow**: Phase 2.8 bedside manner testing
6. **Symptom Management**: Direct tool testing
7. **Error Handling**: Authentication failure scenarios
8. **RLS Compliance**: User data isolation testing

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
│   ├── conversation_manager.py  # Enhanced conversation flow
│   ├── nlp_processor.py   # Advanced NLP processing
│   ├── intent_recognition.py    # Intent detection
│   ├── agent_actions.py   # Symptom management tools
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

- **[AGENT_AWARENESS.md](AGENT_AWARENESS.md)** - Complete agent awareness implementation plan and progress
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

4. **Conversation Flow Issues**
   - Check Phase 2.8 capabilities in health endpoint
   - Verify conversation history format
   - Review intent detection confidence levels

### Debug Commands

```bash
# Check container health and capabilities
curl https://your-container-url/health

# Test enhanced conversation flow
curl -X POST https://your-container-url/chat \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "Hi, how are you?", "context": {"conversation_history": []}}'

# Test symptom logging
curl -X POST https://your-container-url/chat \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "I want to log a headache, severity 7/10, for 3 hours"}'

# Check GPU availability
nvidia-smi

# View container logs
docker logs <container_id>
```

## 🗺️ Future Roadmap

### Short Term (Next Sprint)

#### 🔧 Enhanced Agent Tools
- **Drug Interaction Checker**: Real-time medication safety validation
- **Wearable Data Integration**: Fitness tracker and health device connectivity
- **Lab Results Interpreter**: Automated laboratory result analysis
- **Appointment Scheduling**: Healthcare provider integration

#### 🚀 Conversation Enhancements
- **Multi-language Support**: Conversation flow in multiple languages
- **Voice Integration**: Speech-to-text and text-to-speech capabilities
- **Emotional Intelligence**: Sentiment analysis and empathetic responses
- **Personalization**: Learning user preferences and communication styles

### Medium Term (Future Sprints)

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

### Long Term (Future Quarters)

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
- **Conversation Flow**: Strategy selection and response generation
- **Agent Actions**: Tool usage and symptom tracking activities

### Health Checks

- **Container Health**: `/health` endpoint for real-time status
- **Database Health**: Connection and query performance monitoring
- **GPU Health**: CUDA availability and memory usage
- **Model Health**: BioBERT model loading and inference status
- **Agent Capabilities**: Phase 2.8 conversation management status

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

*Featuring enhanced conversation management with improved bedside manner, intelligent symptom tracking, and a carefully curated set of medical tools designed for privacy, security, and clinical accuracy.*