# Medical AI Assistant - Companion Application Integration Guide

## Overview

This guide provides comprehensive documentation for building a **Medical AI Assistant** companion application that integrates with the TxAgent Hybrid Container. The application combines voice interaction (ElevenLabs), video avatars (TavusAI), and medical document RAG (TxAgent) to provide personalized, confidential medical assistance.

## Architecture Overview

```
User Interface (Frontend)
    ↓
Medical AI Assistant App (Backend)
    ↓
┌─────────────────┬─────────────────┬─────────────────┐
│   ElevenLabs    │    TavusAI      │    TxAgent      │
│   (Voice)       │   (Video)       │  (Medical RAG)  │
└─────────────────┴─────────────────┴─────────────────┘
                    ↓
                Supabase Database
                (RLS Protected)
```

## Required Services

### 1. TxAgent Hybrid Container

- **Purpose**: Medical document embeddings and RAG responses
- **Location**: Your existing container
- **Base URL**: `https://your-txagent-url.com`

### 2. ElevenLabs Voice API

- **Purpose**: Text-to-speech and speech-to-text
- **Website**: https://elevenlabs.io
- **Pricing**: Pay-per-use, ~$0.18/1K characters

### 3. TavusAI Video API

- **Purpose**: AI video avatar generation
- **Website**: https://tavus.io
- **Pricing**: Contact for enterprise pricing

### 4. Supabase Database

- **Purpose**: User data, symptoms, medical documents
- **RLS**: Row Level Security for data isolation
- **Shared**: Uses same database as doctor's portal

## Database Schema

### Required Tables

#### 1. User Symptoms Table

```sql
CREATE TABLE user_symptoms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES auth.users(id) NOT NULL,
  symptom_description TEXT NOT NULL,
  severity INTEGER CHECK (severity >= 1 AND severity <= 10),
  duration_days INTEGER,
  location TEXT, -- body part/area
  triggers TEXT,
  relieving_factors TEXT,
  associated_symptoms TEXT[],
  recorded_at TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS Policy
CREATE POLICY "Users can only access their own symptoms" ON user_symptoms
FOR ALL USING (auth.uid() = user_id);
```

#### 2. Medical Consultations Table

```sql
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
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS Policy
CREATE POLICY "Users can only access their own consultations" ON medical_consultations
FOR ALL USING (auth.uid() = user_id);
```

#### 3. User Medical Profile Table

```sql
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

-- RLS Policy
CREATE POLICY "Users can only access their own medical profile" ON user_medical_profiles
FOR ALL USING (auth.uid() = user_id);
```

## API Endpoints Specification

### Base Configuration

```javascript
const API_CONFIG = {
  txAgent: {
    baseUrl: process.env.TXAGENT_URL,
    timeout: 30000,
  },
  elevenLabs: {
    baseUrl: "https://api.elevenlabs.io/v1",
    apiKey: process.env.ELEVENLABS_API_KEY,
  },
  tavusAI: {
    baseUrl: "https://tavus.io/api/v1",
    apiKey: process.env.TAVUS_API_KEY,
  },
};
```

### 1. Medical Consultation Endpoint

```http
POST /api/medical-consultation
```

**Purpose**: Process user symptoms/queries with multimodal response

**Request Headers:**

```http
Authorization: Bearer <supabase_jwt_token>
Content-Type: application/json
```

**Request Body:**

```json
{
  "query": "I've been having chest pain for 2 days",
  "symptoms": [
    {
      "description": "Sharp chest pain",
      "severity": 7,
      "duration_days": 2,
      "location": "left chest",
      "triggers": "deep breathing"
    }
  ],
  "include_voice": true,
  "include_video": true,
  "voice_model": "elevenlabs_medical_voice",
  "emergency_keywords": ["chest pain", "difficulty breathing"]
}
```

**Response:**

```json
{
  "consultation_id": "uuid-string",
  "response": {
    "text": "Based on your symptoms of chest pain...",
    "urgency_level": "moderate",
    "recommendations": [
      "Seek immediate medical attention",
      "Monitor symptoms closely"
    ]
  },
  "sources": [
    {
      "content": "Chest pain can indicate...",
      "document_title": "Emergency Medicine Guidelines",
      "similarity": 0.89
    }
  ],
  "media": {
    "voice_audio_url": "https://elevenlabs-audio-url.mp3",
    "video_url": "https://tavus-video-url.mp4",
    "voice_processing_time": 1200,
    "video_processing_time": 8500
  },
  "safety": {
    "emergency_detected": false,
    "urgent_care_recommended": true,
    "disclaimer": "This is not a substitute for professional medical advice"
  },
  "processing_time": 3400,
  "created_at": "2025-06-18T10:30:00Z"
}
```

### 2. Symptom Recording Endpoint

```http
POST /api/symptoms
```

**Request Body:**

```json
{
  "symptom_description": "Sharp chest pain on left side",
  "severity": 7,
  "duration_days": 2,
  "location": "left chest",
  "triggers": "deep breathing, physical activity",
  "relieving_factors": "rest",
  "associated_symptoms": ["shortness of breath", "sweating"]
}
```

**Response:**

```json
{
  "symptom_id": "uuid-string",
  "message": "Symptom recorded successfully",
  "recommendations": {
    "urgency": "high",
    "suggested_action": "Seek immediate medical attention"
  }
}
```

### 3. Voice Processing Endpoint

```http
POST /api/voice/process
```

**Purpose**: Convert speech to text and get voice response

**Request Body (multipart/form-data):**

```
audio_file: [audio blob]
response_text: "Your medical response text"
voice_model: "medical_assistant_voice"
```

**Response:**

```json
{
  "transcription": "I have been experiencing chest pain",
  "audio_response_url": "https://elevenlabs-audio-url.mp3",
  "processing_time": 1200
}
```

### 4. Video Avatar Endpoint

```http
POST /api/video/generate
```

**Purpose**: Generate AI video avatar delivering medical response

**Request Body:**

```json
{
  "script": "Based on your symptoms, I recommend...",
  "avatar_id": "medical_professional_avatar",
  "voice_audio_url": "https://elevenlabs-audio-url.mp3",
  "background": "medical_office"
}
```

**Response:**

```json
{
  "video_id": "tavus-video-id",
  "video_url": "https://tavus-video-url.mp4",
  "status": "processing",
  "estimated_completion": "2025-06-18T10:35:00Z"
}
```

## Implementation Flow

### Complete Medical Consultation Flow

```javascript
const processMedicalConsultation = async (userQuery, symptoms, jwt) => {
  const consultation = {
    id: generateUUID(),
    startTime: Date.now(),
  };

  try {
    // Step 1: Record symptoms in database
    const symptomRecords = await recordSymptoms(symptoms, jwt);

    // Step 2: Build comprehensive query for TxAgent
    const ragQuery = buildMedicalQuery(userQuery, symptoms);

    // Step 3: Get medical RAG response from TxAgent
    const ragResponse = await callTxAgentRAG(ragQuery, jwt);

    // Step 4: Generate voice response (parallel)
    const voicePromise = generateVoiceResponse(ragResponse.response);

    // Step 5: Generate video response (parallel)
    const videoPromise = generateVideoResponse(ragResponse.response);

    // Step 6: Wait for media generation
    const [voiceResult, videoResult] = await Promise.all([
      voicePromise,
      videoPromise,
    ]);

    // Step 7: Save consultation record
    const consultationRecord = await saveConsultation(
      {
        ...consultation,
        query: userQuery,
        response: ragResponse.response,
        sources: ragResponse.sources,
        voice_audio_url: voiceResult.url,
        video_url: videoResult.url,
        processing_time: Date.now() - consultation.startTime,
      },
      jwt
    );

    return {
      consultation_id: consultation.id,
      response: ragResponse,
      media: {
        voice_audio_url: voiceResult.url,
        video_url: videoResult.url,
      },
      urgency_assessment: assessUrgency(symptoms, ragResponse),
      safety_disclaimer: getMedicalDisclaimer(),
    };
  } catch (error) {
    logger.error("Medical consultation failed:", error);
    throw new Error("Failed to process medical consultation");
  }
};
```

### TxAgent Integration

```javascript
const callTxAgentRAG = async (query, jwt) => {
  const response = await fetch(`${API_CONFIG.txAgent.baseUrl}/chat`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${jwt}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query: query,
      top_k: 5,
      temperature: 0.3, // Lower temperature for medical accuracy
      history: [], // Include conversation history if available
    }),
  });

  if (!response.ok) {
    throw new Error(`TxAgent error: ${response.status}`);
  }

  return await response.json();
};
```

### ElevenLabs Voice Integration

```javascript
const generateVoiceResponse = async (text) => {
  const response = await fetch(
    `${API_CONFIG.elevenLabs.baseUrl}/text-to-speech/voice-id`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${API_CONFIG.elevenLabs.apiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text: text,
        voice_settings: {
          stability: 0.75,
          similarity_boost: 0.75,
          style: 0.2,
          use_speaker_boost: true,
        },
        model_id: "eleven_multilingual_v2",
      }),
    }
  );

  const audioBlob = await response.blob();
  const audioUrl = await uploadAudioToStorage(audioBlob);

  return { url: audioUrl, duration: estimateAudioDuration(text) };
};
```

### TavusAI Video Integration

```javascript
const generateVideoResponse = async (text, voiceAudioUrl) => {
  const response = await fetch(`${API_CONFIG.tavusAI.baseUrl}/videos`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${API_CONFIG.tavusAI.apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      script: text,
      replica_id: "medical_professional_replica",
      audio_url: voiceAudioUrl,
      background: "medical_office",
      video_name: `medical_consultation_${Date.now()}`,
    }),
  });

  const result = await response.json();

  // Poll for completion
  return await pollVideoCompletion(result.video_id);
};
```

## Security & Privacy Considerations

### 1. HIPAA Compliance

```javascript
const securityConfig = {
  encryption: {
    atRest: true,
    inTransit: true,
    keyRotation: "90days",
  },
  auditLogging: {
    enabled: true,
    includeUserData: false,
    retentionPeriod: "7years",
  },
  dataRetention: {
    consultations: "7years",
    audioFiles: "1year",
    videoFiles: "1year",
    symptoms: "indefinite", // User controlled
  },
};
```

### 2. Row Level Security (RLS)

```sql
-- Ensure all tables have proper RLS
ALTER TABLE user_symptoms ENABLE ROW LEVEL SECURITY;
ALTER TABLE medical_consultations ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_medical_profiles ENABLE ROW LEVEL SECURITY;

-- Users can only access documents they have permission for
CREATE POLICY "Users can access shared medical documents" ON documents
FOR SELECT USING (
  auth.uid() = user_id OR
  EXISTS (
    SELECT 1 FROM document_permissions
    WHERE document_id = documents.id
    AND user_id = auth.uid()
    AND permission_type = 'read'
  )
);
```

### 3. Emergency Detection

```javascript
const emergencyKeywords = [
  "chest pain",
  "difficulty breathing",
  "severe bleeding",
  "unconscious",
  "stroke symptoms",
  "heart attack",
  "severe allergic reaction",
  "poisoning",
];

const assessUrgency = (symptoms, ragResponse) => {
  const emergencyDetected = symptoms.some((symptom) =>
    emergencyKeywords.some((keyword) =>
      symptom.description.toLowerCase().includes(keyword)
    )
  );

  if (emergencyDetected || symptoms.some((s) => s.severity >= 9)) {
    return {
      level: "emergency",
      message: "CALL 911 IMMEDIATELY",
      showEmergencyBanner: true,
    };
  }

  // Additional urgency logic...
  return assessBasedOnRAGResponse(ragResponse);
};
```

## Environment Variables

```bash
# TxAgent Container
TXAGENT_URL=https://your-txagent-container-url
TXAGENT_TIMEOUT=30000

# ElevenLabs
ELEVENLABS_API_KEY=your-elevenlabs-api-key
ELEVENLABS_VOICE_ID=your-medical-voice-id

# TavusAI
TAVUS_API_KEY=your-tavus-api-key
TAVUS_REPLICA_ID=your-medical-avatar-id

# Supabase (shared with doctor portal)
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# Medical Safety
EMERGENCY_WEBHOOK_URL=your-emergency-notification-webhook
MEDICAL_DISCLAIMER_REQUIRED=true
ENABLE_EMERGENCY_DETECTION=true

# Media Storage
AUDIO_STORAGE_BUCKET=medical-audio
VIDEO_STORAGE_BUCKET=medical-videos
MEDIA_RETENTION_DAYS=365
```

## Frontend Integration Example

### React Component

```jsx
import { useState, useRef } from "react";
import { supabase } from "../lib/supabase";

const MedicalAssistant = () => {
  const [recording, setRecording] = useState(false);
  const [consultation, setConsultation] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleVoiceInput = async (audioBlob) => {
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append("audio", audioBlob);

      const response = await fetch("/api/voice/transcribe", {
        method: "POST",
        headers: {
          Authorization: `Bearer ${await getJWT()}`,
        },
        body: formData,
      });

      const { transcription } = await response.json();
      await processMedicalQuery(transcription);
    } catch (error) {
      console.error("Voice processing failed:", error);
    } finally {
      setLoading(false);
    }
  };

  const processMedicalQuery = async (query) => {
    const response = await fetch("/api/medical-consultation", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${await getJWT()}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query: query,
        include_voice: true,
        include_video: true,
      }),
    });

    const consultationResult = await response.json();
    setConsultation(consultationResult);
  };

  return (
    <div className="medical-assistant">
      {consultation?.safety?.emergency_detected && (
        <div className="emergency-banner">
          🚨 EMERGENCY DETECTED - CALL 911 IMMEDIATELY
        </div>
      )}

      <VoiceRecorder onRecording={handleVoiceInput} />

      {consultation && (
        <ConsultationResponse
          response={consultation.response}
          audioUrl={consultation.media?.voice_audio_url}
          videoUrl={consultation.media?.video_url}
          sources={consultation.sources}
        />
      )}

      <MedicalDisclaimer />
    </div>
  );
};
```

## Testing & Deployment

### 1. Test Scenarios

```javascript
const testScenarios = [
  {
    name: "Normal symptom inquiry",
    input: "I have a mild headache",
    expectedUrgency: "low",
  },
  {
    name: "Emergency detection",
    input: "I am having severe chest pain and difficulty breathing",
    expectedUrgency: "emergency",
  },
  {
    name: "Medical document reference",
    input: "What are the side effects of metformin?",
    expectedSources: ["medication_guide.pdf"],
  },
];
```

### 2. Performance Monitoring

```javascript
const performanceMetrics = {
  txAgentResponseTime: "<3000ms",
  voiceGenerationTime: "<2000ms",
  videoGenerationTime: "<10000ms",
  totalConsultationTime: "<15000ms",
  concurrentUsers: "100+",
  uptime: "99.9%",
};
```

## Cost Estimation

### Monthly Usage (1000 consultations)

- **ElevenLabs**: ~$180 (1K chars avg per response)
- **TavusAI**: Contact for pricing (enterprise)
- **TxAgent**: Compute costs only (your container)
- **Supabase**: ~$25-50 (database + storage)
- **Total**: ~$255-280 + TavusAI costs

## Support & Troubleshooting

### Common Issues

1. **TxAgent 404 errors**: Check JWT authentication
2. **Voice generation fails**: Verify ElevenLabs API key
3. **Video processing timeout**: TavusAI videos take 5-15 seconds
4. **RLS access denied**: Verify user permissions

### Emergency Fallbacks

- If TxAgent fails: Use fallback medical knowledge base
- If voice fails: Return text-only response
- If video fails: Continue with voice response
- If all AI fails: Display emergency contact information

## TxAgent Container Integration Details

### Authentication Flow

```javascript
// Ensure every request to TxAgent includes JWT
const authenticatedTxAgentClient = axios.create({
  baseURL: process.env.TXAGENT_URL,
  timeout: 30000,
});

authenticatedTxAgentClient.interceptors.request.use(async (config) => {
  const {
    data: { session },
  } = await supabase.auth.getSession();
  if (session?.access_token) {
    config.headers.Authorization = `Bearer ${session.access_token}`;
  }
  return config;
});
```

### Available TxAgent Endpoints

```javascript
// Document processing (if user uploads their own documents)
POST /process-document
{
  "file_path": "user_id/document.pdf",
  "metadata": {"source": "user_upload"}
}

// Text embedding for symptom analysis
POST /embed
{
  "text": "Patient reports chest pain and shortness of breath",
  "normalize": true
}

// RAG chat for medical consultation
POST /chat
{
  "query": "What could cause chest pain and shortness of breath?",
  "top_k": 5,
  "temperature": 0.3
}

// Check processing status
GET /embedding-jobs/{job_id}
```

### Medical Query Enhancement

```javascript
const buildMedicalQuery = (userQuery, symptoms) => {
  const symptomContext = symptoms
    .map(
      (s) =>
        `Symptom: ${s.description}, Severity: ${s.severity}/10, Duration: ${s.duration_days} days, Location: ${s.location}`
    )
    .join(". ");

  return `
    Patient Query: ${userQuery}
    
    Current Symptoms: ${symptomContext}
    
    Please provide medical information relevant to these symptoms, including:
    1. Potential causes
    2. Urgency assessment 
    3. Recommended next steps
    4. Warning signs that require immediate attention
    
    Base your response on medical literature and guidelines.
  `;
};
```

This comprehensive guide provides everything needed to build a secure, HIPAA-compliant medical AI assistant that leverages your existing TxAgent container and medical document database while adding voice and video capabilities for an enhanced user experience.
