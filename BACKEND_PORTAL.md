# Backend Portal Integration Plan for TxAgent Medical RAG System

## Overview

This document provides a complete integration plan for adding TxAgent Medical RAG capabilities to the existing Doctor's Portal backend. The portal will serve as an intermediary between the mobile user application (SymptomSavior) and the TxAgent container, orchestrating medical consultations, document processing, and multimedia generation.

## System Architecture

```
Mobile App (SymptomSavior) 
    ↓ JWT + Request
Doctor's Portal Backend (Node.js/Express)
    ↓ JWT Forwarding + Orchestration
┌─────────────────┬─────────────────┬─────────────────┐
│   TxAgent       │   ElevenLabs    │    TavusAI      │
│  Container      │    (Voice)      │   (Video)       │
└─────────────────┴─────────────────┴─────────────────┘
                    ↓
                Supabase Database
                (RLS Protected)
```

## Required Environment Variables

Add these environment variables to your Doctor's Portal backend:

```bash
# TxAgent Container Configuration
TXAGENT_CONTAINER_URL=https://your-txagent-url.proxy.runpod.net
TXAGENT_TIMEOUT=30000

# ElevenLabs Voice API
ELEVENLABS_API_KEY=your-elevenlabs-api-key
ELEVENLABS_VOICE_ID=your-medical-voice-id

# TavusAI Video API
TAVUS_API_KEY=your-tavus-api-key
TAVUS_REPLICA_ID=your-medical-avatar-id

# Supabase (shared with existing portal)
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Medical Safety Configuration
EMERGENCY_WEBHOOK_URL=your-emergency-notification-webhook
MEDICAL_DISCLAIMER_REQUIRED=true
ENABLE_EMERGENCY_DETECTION=true

# Media Storage
AUDIO_STORAGE_BUCKET=medical-audio
VIDEO_STORAGE_BUCKET=medical-videos
MEDIA_RETENTION_DAYS=365
```

## Required Database Tables

The following tables need to be added to your existing Supabase database. **Note**: The core TxAgent tables (`documents`, `embedding_jobs`, `agents`) should already exist from the consolidated migration.

### Additional Tables for User App Integration

```sql
-- User symptoms tracking
CREATE TABLE user_symptoms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  symptom_description TEXT NOT NULL,
  severity INTEGER CHECK (severity >= 1 AND severity <= 10),
  duration_days INTEGER,
  location TEXT,
  triggers TEXT,
  relieving_factors TEXT,
  associated_symptoms TEXT[],
  recorded_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Medical consultations log
CREATE TABLE medical_consultations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  session_id TEXT NOT NULL,
  query TEXT NOT NULL,
  response TEXT NOT NULL,
  sources JSONB DEFAULT '[]',
  voice_audio_url TEXT,
  video_url TEXT,
  consultation_type TEXT DEFAULT 'symptom_inquiry',
  processing_time INTEGER,
  emergency_detected BOOLEAN DEFAULT FALSE,
  context_used JSONB DEFAULT '{}',
  confidence_score FLOAT,
  recommendations JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- User medical profiles
CREATE TABLE user_medical_profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  age INTEGER,
  gender TEXT,
  medical_conditions TEXT[],
  medications TEXT[],
  allergies TEXT[],
  emergency_contact JSONB,
  preferred_language TEXT DEFAULT 'en',
  voice_preferences JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS on all new tables
ALTER TABLE user_symptoms ENABLE ROW LEVEL SECURITY;
ALTER TABLE medical_consultations ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_medical_profiles ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can only access their own symptoms" ON user_symptoms
FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can only access their own consultations" ON medical_consultations
FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "Users can only access their own medical profile" ON user_medical_profiles
FOR ALL USING (auth.uid() = user_id);
```

## Required API Endpoints

### 1. Medical Consultation Endpoint

**Route**: `POST /api/medical-consultation`

**Purpose**: Primary endpoint for AI-powered medical consultations with multimodal response generation.

**Request Headers**:
```
Authorization: Bearer <supabase_jwt_token>  // CRITICAL: User's JWT from mobile app
Content-Type: application/json
User-Agent: SymptomSavior/1.0.0
```

**Request Body**:
```typescript
interface MedicalConsultationRequest {
  query: string;                    // User's medical question
  context?: {                       // Optional user context
    user_profile?: any;
    recent_symptoms?: any[];
    medical_conditions?: any[];
    current_medications?: any[];
    allergies?: any[];
    recent_visits?: any[];
  };
  include_voice?: boolean;          // Generate voice response
  include_video?: boolean;          // Generate video response
  session_id?: string;              // Optional session tracking
  timestamp?: string;               // Request timestamp
}
```

**Response Body**:
```typescript
interface MedicalConsultationResponse {
  response: {
    text: string;                   // AI-generated response
    sources?: Array<{
      title: string;
      content: string;
      relevance_score: number;
    }>;
    confidence_score?: number;
  };
  safety: {
    emergency_detected: boolean;    // Emergency keyword detection
    disclaimer: string;             // Medical disclaimer
    urgent_care_recommended?: boolean;
  };
  media?: {
    voice_audio_url?: string;       // ElevenLabs audio URL
    video_url?: string;             // TavusAI video URL
  };
  recommendations?: {
    suggested_action?: string;
    follow_up_questions?: string[];
  };
  processing_time_ms: number;
  session_id: string;
}
```

**Implementation Flow**:
1. Extract JWT from Authorization header
2. Log incoming request with user context
3. Record symptoms in `user_symptoms` table (if provided)
4. Call TxAgent `/chat` endpoint with forwarded JWT
5. Generate voice response via ElevenLabs (if requested)
6. Generate video response via TavusAI (if requested)
7. Log complete consultation in `medical_consultations` table
8. Return aggregated response

### 2. Document Processing Endpoint

**Route**: `POST /api/process-document`

**Purpose**: Process user-uploaded medical documents for RAG integration.

**Request Headers**:
```
Authorization: Bearer <supabase_jwt_token>
Content-Type: application/json
```

**Request Body**:
```typescript
interface DocumentProcessingRequest {
  file_path: string;                // Path in Supabase Storage
  metadata: {
    title?: string;
    author?: string;
    category?: string;
    year?: string;
    source?: string;
    document_type?: string;
    keywords?: string[];
  };
}
```

**Response Body**:
```typescript
interface DocumentProcessingResponse {
  job_id: string;                   // Background job identifier
  status: 'pending' | 'processing' | 'completed' | 'failed';
  message: string;
  estimated_completion?: string;
}
```

**Implementation Flow**:
1. Extract JWT and validate user access to file
2. Forward request to TxAgent `/process-document` endpoint
3. Return job tracking information

### 3. Job Status Endpoint

**Route**: `GET /api/embedding-jobs/:job_id`

**Purpose**: Check document processing job status.

**Request Headers**:
```
Authorization: Bearer <supabase_jwt_token>
```

**Response Body**:
```typescript
interface JobStatusResponse {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  chunk_count?: number;
  document_ids?: string[];
  error?: string;
  message: string;
  progress_percentage?: number;
}
```

### 4. Voice Processing Endpoint

**Route**: `POST /api/voice/process`

**Purpose**: Handle speech-to-text and text-to-speech operations.

**Request Body** (multipart/form-data):
```
audio_file: [audio blob]
response_text: "Your medical response text"
voice_model: "medical_assistant_voice"
```

**Response Body**:
```typescript
interface VoiceProcessingResponse {
  transcription?: string;           // Speech-to-text result
  audio_response_url?: string;      // Text-to-speech result
  processing_time: number;
}
```

### 5. Video Generation Endpoint

**Route**: `POST /api/video/generate`

**Purpose**: Generate AI video avatar delivering medical response.

**Request Body**:
```typescript
interface VideoGenerationRequest {
  script: string;                   // Text to be spoken
  avatar_id?: string;               // TavusAI avatar identifier
  voice_audio_url?: string;         // Pre-generated audio
  background?: string;              // Video background setting
}
```

**Response Body**:
```typescript
interface VideoGenerationResponse {
  video_id: string;                 // TavusAI video identifier
  video_url?: string;               // Final video URL (when ready)
  status: 'processing' | 'completed' | 'failed';
  estimated_completion?: string;
}
```

## Authentication & Security Implementation

### JWT Token Handling

**Critical Requirements**:
1. **Never validate JWT locally** - always forward to TxAgent container
2. **Always include original JWT** in requests to TxAgent endpoints
3. **Use JWT for all Supabase operations** to ensure RLS compliance

**Example Implementation**:
```javascript
// Extract JWT from request
const extractJWT = (req) => {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    throw new Error('Missing or invalid Authorization header');
  }
  return authHeader.split(' ')[1];
};

// Forward JWT to TxAgent
const callTxAgent = async (endpoint, data, jwt) => {
  const response = await fetch(`${process.env.TXAGENT_CONTAINER_URL}${endpoint}`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${jwt}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(data)
  });
  return response.json();
};
```

### Row Level Security (RLS) Compliance

**Key Points**:
- All database operations automatically filter by user via RLS
- JWT `sub` claim contains user ID for filtering
- No manual user filtering needed in queries
- TxAgent container handles RLS for document operations

### Emergency Detection & Safety

**Implementation Requirements**:
```javascript
const emergencyKeywords = [
  'chest pain', 'difficulty breathing', 'severe bleeding',
  'unconscious', 'heart attack', 'stroke', 'seizure',
  'severe allergic reaction', 'suicidal thoughts', 'overdose'
];

const detectEmergency = (text, severity) => {
  const hasKeywords = emergencyKeywords.some(keyword => 
    text.toLowerCase().includes(keyword)
  );
  const highSeverity = severity >= 9;
  
  return {
    isEmergency: hasKeywords || highSeverity,
    confidence: hasKeywords && highSeverity ? 'high' : 'medium'
  };
};
```

## External Service Integration

### ElevenLabs Voice API

**Configuration**:
```javascript
const generateVoiceResponse = async (text) => {
  const response = await fetch(
    `https://api.elevenlabs.io/v1/text-to-speech/${process.env.ELEVENLABS_VOICE_ID}`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${process.env.ELEVENLABS_API_KEY}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        text: text,
        voice_settings: {
          stability: 0.75,
          similarity_boost: 0.75,
          style: 0.2,
          use_speaker_boost: true
        },
        model_id: 'eleven_multilingual_v2'
      })
    }
  );
  
  const audioBlob = await response.blob();
  const audioUrl = await uploadAudioToStorage(audioBlob);
  return { url: audioUrl, duration: estimateAudioDuration(text) };
};
```

### TavusAI Video API

**Configuration**:
```javascript
const generateVideoResponse = async (text, voiceAudioUrl) => {
  const response = await fetch('https://tavus.io/api/v1/videos', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${process.env.TAVUS_API_KEY}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      script: text,
      replica_id: process.env.TAVUS_REPLICA_ID,
      audio_url: voiceAudioUrl,
      background: 'medical_office',
      video_name: `medical_consultation_${Date.now()}`
    })
  });
  
  const result = await response.json();
  return await pollVideoCompletion(result.video_id);
};
```

## Error Handling & Logging

### Comprehensive Logging Strategy

**Required Log Events**:
1. **Request Start**: Log all incoming requests with user context
2. **JWT Validation**: Log JWT forwarding and validation results
3. **TxAgent Calls**: Log all calls to TxAgent container with response status
4. **External API Calls**: Log ElevenLabs and TavusAI interactions
5. **Database Operations**: Log Supabase operations and RLS compliance
6. **Emergency Detection**: Log all emergency detection events
7. **Error Events**: Log all errors with full context for debugging

**Example Logging Implementation**:
```javascript
const logger = {
  info: (message, context) => console.log(JSON.stringify({ level: 'info', message, context, timestamp: new Date().toISOString() })),
  error: (message, error, context) => console.error(JSON.stringify({ level: 'error', message, error: error.message, context, timestamp: new Date().toISOString() })),
  warn: (message, context) => console.warn(JSON.stringify({ level: 'warn', message, context, timestamp: new Date().toISOString() }))
};

// Usage in endpoints
app.post('/api/medical-consultation', async (req, res) => {
  const startTime = Date.now();
  let jwt, userId;
  
  try {
    jwt = extractJWT(req);
    logger.info('Medical consultation request started', { 
      query: req.body.query?.substring(0, 100),
      hasContext: !!req.body.context,
      includeVoice: req.body.include_voice,
      includeVideo: req.body.include_video
    });
    
    // ... implementation
    
    logger.info('Medical consultation completed', {
      processingTime: Date.now() - startTime,
      userId: userId,
      emergencyDetected: result.safety.emergency_detected
    });
    
  } catch (error) {
    logger.error('Medical consultation failed', error, {
      processingTime: Date.now() - startTime,
      userId: userId,
      query: req.body.query?.substring(0, 100)
    });
    res.status(500).json({ error: 'Medical consultation failed' });
  }
});
```

### Error Response Standards

**Standard Error Responses**:
```javascript
// Authentication errors
{ error: 'Authentication failed. Please sign in again.', code: 'AUTH_FAILED' }

// Rate limiting
{ error: 'Too many requests. Please wait a moment and try again.', code: 'RATE_LIMITED' }

// Service unavailable
{ error: 'Medical consultation service is temporarily unavailable.', code: 'SERVICE_UNAVAILABLE' }

// Emergency detected
{ 
  error: 'Emergency symptoms detected. Please contact emergency services immediately.',
  code: 'EMERGENCY_DETECTED',
  emergency_info: {
    detected_keywords: ['chest pain'],
    recommended_action: 'Call 911 immediately'
  }
}
```

## Performance & Monitoring

### Response Time Targets

- **Medical Consultation**: < 5 seconds (without media)
- **With Voice**: < 8 seconds
- **With Video**: < 15 seconds
- **Document Processing**: < 30 seconds (background job)

### Health Check Endpoint

**Route**: `GET /api/health/medical-rag`

**Response**:
```json
{
  "status": "healthy",
  "services": {
    "txagent": "connected",
    "elevenlabs": "connected",
    "tavus": "connected",
    "supabase": "connected"
  },
  "version": "1.0.0",
  "uptime": 3600,
  "last_check": "2025-01-08T12:00:00Z"
}
```

## Testing & Validation

### Required Test Scenarios

1. **Basic Medical Consultation**: Simple query without media
2. **Emergency Detection**: Query with emergency keywords
3. **Voice Generation**: Consultation with voice response
4. **Video Generation**: Consultation with video response
5. **Document Processing**: Upload and process medical document
6. **Authentication Failure**: Invalid JWT handling
7. **Service Unavailable**: TxAgent container offline
8. **Rate Limiting**: Multiple rapid requests

### Postman Collection Integration

The existing `TxAgent_API_Tests.postman_collection.json` should be extended with new tests for the portal endpoints:

```json
{
  "name": "Portal Medical Consultation",
  "request": {
    "method": "POST",
    "header": [
      {
        "key": "Authorization",
        "value": "Bearer {{user_jwt_token}}"
      }
    ],
    "url": "{{portal_base_url}}/api/medical-consultation",
    "body": {
      "mode": "raw",
      "raw": "{\n  \"query\": \"I have been experiencing chest pain\",\n  \"include_voice\": true,\n  \"include_video\": false\n}"
    }
  }
}
```

## Deployment Considerations

### Environment-Specific Configuration

**Development**:
```bash
TXAGENT_CONTAINER_URL=http://localhost:8000
ENABLE_EMERGENCY_DETECTION=false
LOG_LEVEL=debug
```

**Production**:
```bash
TXAGENT_CONTAINER_URL=https://your-production-txagent-url.proxy.runpod.net
ENABLE_EMERGENCY_DETECTION=true
LOG_LEVEL=info
EMERGENCY_WEBHOOK_URL=https://your-emergency-notification-service.com/webhook
```

### Security Checklist

- [ ] All environment variables properly configured
- [ ] JWT forwarding implemented correctly
- [ ] RLS policies tested and working
- [ ] Emergency detection system tested
- [ ] Rate limiting implemented
- [ ] CORS configured for mobile app domain
- [ ] HTTPS enforced in production
- [ ] Error messages don't leak sensitive information
- [ ] Audit logging enabled for all medical consultations

## Support & Troubleshooting

### Common Issues

1. **401 Unauthorized from TxAgent**: JWT not forwarded correctly
2. **RLS Policy Violations**: User ID mismatch in JWT
3. **Empty Chat Responses**: No documents processed for user
4. **Voice/Video Generation Failures**: API key configuration issues
5. **Slow Response Times**: TxAgent container resource constraints

### Debug Commands

```bash
# Test TxAgent connectivity
curl -X GET "${TXAGENT_CONTAINER_URL}/health"

# Test with authentication
curl -X POST "${TXAGENT_CONTAINER_URL}/chat" \
  -H "Authorization: Bearer ${TEST_JWT}" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'

# Check Supabase connection
curl -X GET "${SUPABASE_URL}/rest/v1/documents" \
  -H "Authorization: Bearer ${TEST_JWT}" \
  -H "apikey: ${SUPABASE_ANON_KEY}"
```

## Implementation Priority

### Phase 1: Core Functionality (Week 1)
1. Implement `/api/medical-consultation` endpoint
2. Set up JWT forwarding to TxAgent
3. Basic error handling and logging
4. Test with mobile app integration

### Phase 2: Enhanced Features (Week 2)
1. Add voice generation via ElevenLabs
2. Implement emergency detection
3. Add comprehensive logging
4. Document processing endpoints

### Phase 3: Advanced Features (Week 3)
1. Video generation via TavusAI
2. Performance optimization
3. Advanced monitoring and health checks
4. Production deployment and testing

This integration plan provides everything needed to successfully add TxAgent Medical RAG capabilities to your existing Doctor's Portal backend, serving as a robust intermediary for the mobile user application.