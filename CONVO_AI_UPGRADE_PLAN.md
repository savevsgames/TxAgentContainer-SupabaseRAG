# Conversational AI Upgrade Plan for Symptom Savior

## Overview

This document outlines a comprehensive plan to enhance the Symptom Savior application with real-time conversational AI capabilities using ElevenLabs Conversational AI platform integrated with TxAgent's medical knowledge base. The goal is to transform the current turn-based interaction model into a natural, continuous conversation experience.

## Current State Analysis

### Existing Infrastructure ✅
- **Backend Voice Services**: `/api/voice/tts` and `/api/voice/transcribe` endpoints working
- **TxAgent Integration**: Medical consultation endpoint with context awareness
- **Medical Profile System**: Comprehensive user health data available
- **Authentication**: JWT-based security with RLS policies
- **Audio Storage**: Supabase storage with proper user isolation

### Current Limitations 🔧
- **Turn-based Interaction**: Manual start/stop recording
- **Audio Format Issues**: MediaRecorder format compatibility (fixed: now using `audio/webm`)
- **Latency**: Multiple round-trips for STT → AI → TTS
- **Context Loss**: Each interaction is somewhat isolated
- **No Interruption Support**: Cannot interrupt AI responses

## Target State: Natural Medical Conversations

### Core Experience Goals
1. **Continuous Listening**: Tap once to start a medical consultation session
2. **Natural Turn-Taking**: AI detects when user finishes speaking
3. **Contextual Memory**: Maintains full conversation and medical history
4. **Interruption Support**: User can interrupt AI responses naturally
5. **Medical Safety**: Real-time emergency detection with immediate escalation
6. **Personalized Responses**: Leverages user's medical profile throughout conversation

## Implementation Strategy

### Phase 1: Enhanced Audio Foundation (Week 1-2)

#### 1.1 Fix Current Audio Issues ✅ COMPLETED
- ✅ Fixed MediaRecorder format to use `audio/webm`
- ✅ TTS playback working with proper audio element handling
- ✅ User-authenticated Supabase storage upload working

#### 1.2 Streaming Audio Infrastructure
```typescript
// New WebSocket endpoint for real-time conversation
POST /api/conversation/start
WebSocket /api/conversation/stream

// Enhanced audio capture with VAD
interface AudioStreamConfig {
  format: 'audio/webm',
  sampleRate: 16000,
  channels: 1,
  chunkDuration: 200, // ms
  vadThreshold: 0.5,
  silenceTimeout: 1500 // ms before processing
}
```

#### 1.3 Voice Activity Detection (VAD)
- **Client-Side VAD**: Use WebRTC VAD for low latency
- **Fallback Server VAD**: For browsers without WebRTC support
- **Adaptive Thresholds**: Adjust based on ambient noise

### Phase 2: ElevenLabs Conversational AI Integration (Week 3-4)

#### 2.1 ElevenLabs Conversational AI Setup
```javascript
// New service for ElevenLabs Conversational AI
class ElevenLabsConversationService {
  async startConversation(userProfile, medicalContext) {
    // Initialize conversation with medical context
    const conversationConfig = {
      agent_id: process.env.ELEVENLABS_AGENT_ID,
      user_context: {
        medical_profile: userProfile,
        conversation_type: 'medical_consultation',
        safety_mode: 'high'
      }
    };
    
    return await this.createConversationSession(conversationConfig);
  }
  
  async streamAudioToConversation(audioChunk, sessionId) {
    // Stream audio directly to ElevenLabs
    return await this.sendAudioChunk(sessionId, audioChunk);
  }
}
```

#### 2.2 TxAgent Knowledge Integration
```javascript
// Hybrid approach: ElevenLabs for conversation + TxAgent for medical knowledge
class HybridMedicalConversation {
  async enhanceWithMedicalKnowledge(query, userContext) {
    // Get relevant medical documents from TxAgent
    const medicalContext = await this.txAgentService.searchMedicalKnowledge(
      query, 
      userContext.medical_profile
    );
    
    // Inject into ElevenLabs conversation context
    return this.elevenLabsService.updateConversationContext(
      sessionId, 
      medicalContext
    );
  }
}
```

### Phase 3: Real-Time Conversation Flow (Week 5-6)

#### 3.1 WebSocket Conversation Protocol
```typescript
interface ConversationMessage {
  type: 'audio_chunk' | 'transcript_partial' | 'transcript_final' | 
        'ai_thinking' | 'ai_speaking' | 'ai_response_complete' | 
        'emergency_detected' | 'conversation_end';
  payload: any;
  timestamp: number;
  session_id: string;
  user_id: string;
  medical_context?: UserMedicalProfile;
}

// Real-time conversation states
enum ConversationState {
  LISTENING = 'listening',           // User is speaking
  PROCESSING = 'processing',         // AI is thinking
  RESPONDING = 'responding',         // AI is speaking
  WAITING = 'waiting',              // Waiting for user input
  EMERGENCY = 'emergency',          // Emergency detected
  ENDED = 'ended'                   // Conversation ended
}
```

#### 3.2 Enhanced Medical Context Management
```javascript
class MedicalConversationManager {
  constructor(userProfile, conversationHistory) {
    this.medicalContext = {
      profile: userProfile,
      current_symptoms: [],
      mentioned_medications: [],
      emergency_keywords: [],
      conversation_summary: '',
      risk_level: 'low'
    };
  }
  
  async updateContextFromTranscript(transcript) {
    // Extract medical entities in real-time
    const entities = await this.extractMedicalEntities(transcript);
    
    // Update emergency risk assessment
    const riskAssessment = await this.assessEmergencyRisk(entities);
    
    if (riskAssessment.level === 'high') {
      return this.triggerEmergencyProtocol(riskAssessment);
    }
    
    // Update conversation context
    this.medicalContext = {
      ...this.medicalContext,
      ...entities,
      risk_level: riskAssessment.level
    };
  }
}
```

### Phase 4: Advanced Conversation Features (Week 7-8)

#### 4.1 Interruption and Barge-in Support
```typescript
class ConversationInterruptionHandler {
  private isAISpeaking = false;
  private audioPlaybackController: AudioPlaybackController;
  
  async handleUserInterruption(audioChunk: ArrayBuffer) {
    if (this.isAISpeaking) {
      // Stop AI audio immediately
      await this.audioPlaybackController.stop();
      
      // Send interruption signal to ElevenLabs
      await this.conversationService.signalInterruption();
      
      // Process user's interruption
      return this.processUserInput(audioChunk);
    }
  }
}
```

#### 4.2 Medical Safety Enhancements
```javascript
class RealTimeMedicalSafety {
  private emergencyKeywords = [
    'chest pain', 'can\'t breathe', 'severe bleeding', 
    'unconscious', 'heart attack', 'stroke', 'suicide'
  ];
  
  async monitorTranscriptForEmergency(partialTranscript) {
    const emergencyDetected = this.detectEmergencyKeywords(partialTranscript);
    
    if (emergencyDetected.confidence > 0.8) {
      // Immediate interruption of conversation
      await this.interruptConversation();
      
      // Emergency response protocol
      return this.initiateEmergencyResponse(emergencyDetected);
    }
  }
  
  async initiateEmergencyResponse(emergency) {
    // Log emergency event
    await this.logEmergencyEvent(emergency);
    
    // Immediate response to user
    const emergencyResponse = {
      text: "I've detected you may be experiencing a medical emergency. Please contact emergency services immediately by calling 911.",
      priority: 'critical',
      actions: ['call_911', 'contact_emergency_contact']
    };
    
    // Override conversation flow
    return this.sendEmergencyResponse(emergencyResponse);
  }
}
```

### Phase 5: UI/UX Enhancements (Week 9-10)

#### 5.1 Conversational UI Components
```typescript
// New conversation interface components
const ConversationView = () => {
  const { 
    conversationState, 
    transcript, 
    isListening, 
    isAISpeaking,
    medicalContext 
  } = useConversation();
  
  return (
    <View style={styles.conversationContainer}>
      <ConversationHeader 
        state={conversationState}
        medicalContext={medicalContext}
      />
      
      <ConversationTranscript 
        messages={transcript}
        isLive={isListening || isAISpeaking}
      />
      
      <AudioVisualizer 
        isListening={isListening}
        isAISpeaking={isAISpeaking}
        audioLevel={audioLevel}
      />
      
      <ConversationControls
        onStartConversation={startConversation}
        onEndConversation={endConversation}
        onEmergency={triggerEmergency}
        state={conversationState}
      />
    </View>
  );
};
```

#### 5.2 Real-Time Visual Feedback
```typescript
const AudioVisualizer = ({ isListening, isAISpeaking, audioLevel }) => {
  return (
    <View style={styles.visualizer}>
      {isListening && (
        <WaveformVisualizer 
          audioLevel={audioLevel}
          color="#4CAF50"
          label="Listening..."
        />
      )}
      
      {isAISpeaking && (
        <AIResponseIndicator 
          isAnimated={true}
          color="#2196F3"
          label="AI is responding..."
        />
      )}
      
      <ConversationStateIndicator state={conversationState} />
    </View>
  );
};
```

## Technical Architecture

### Backend Services Architecture

```
ConversationalAI/
├── services/
│   ├── ElevenLabsConversationService.js    # ElevenLabs integration
│   ├── TxAgentKnowledgeService.js          # Medical knowledge retrieval
│   ├── HybridConversationOrchestrator.js   # Combines both services
│   ├── MedicalSafetyMonitor.js             # Real-time safety monitoring
│   └── ConversationSessionManager.js       # Session state management
├── websocket/
│   ├── ConversationWebSocketHandler.js     # WebSocket message handling
│   ├── AudioStreamProcessor.js             # Audio chunk processing
│   └── RealTimeTranscriptProcessor.js      # Live transcript handling
├── models/
│   ├── ConversationSession.js              # Session data model
│   ├── MedicalConversationContext.js       # Medical context model
│   └── EmergencyEvent.js                   # Emergency event model
└── utils/
    ├── VoiceActivityDetection.js           # Server-side VAD
    ├── MedicalEntityExtraction.js          # Extract medical terms
    └── ConversationMetrics.js              # Performance monitoring
```

### Frontend Architecture

```
ConversationalAI/
├── hooks/
│   ├── useConversation.ts                  # Main conversation hook
│   ├── useStreamingAudio.ts               # Audio streaming management
│   ├── useVoiceActivityDetection.ts       # Client-side VAD
│   └── useMedicalSafety.ts                # Safety monitoring
├── components/
│   ├── ConversationView.tsx               # Main conversation UI
│   ├── AudioVisualizer.tsx                # Real-time audio visualization
│   ├── ConversationTranscript.tsx         # Live transcript display
│   ├── MedicalContextPanel.tsx            # Show relevant medical info
│   └── EmergencyAlert.tsx                 # Emergency response UI
├── services/
│   ├── ConversationWebSocketService.ts    # WebSocket communication
│   ├── AudioStreamingService.ts           # Audio capture/playback
│   └── MedicalContextService.ts           # Medical data management
└── utils/
    ├── AudioProcessingUtils.ts             # Audio processing helpers
    ├── ConversationStateManager.ts         # State management
    └── EmergencyProtocols.ts               # Emergency response logic
```

## Data Flow Architecture

### 1. Conversation Initiation
```
User Tap → Load Medical Profile → Initialize ElevenLabs Session → 
Start Audio Streaming → Begin Conversation
```

### 2. Real-Time Audio Processing
```
Microphone → VAD → Audio Chunks → WebSocket → 
ElevenLabs Conversational AI → Real-time Response
```

### 3. Medical Knowledge Enhancement
```
User Query → Extract Medical Entities → Query TxAgent → 
Inject Medical Context → Enhanced AI Response
```

### 4. Emergency Detection Flow
```
Audio Stream → Real-time Transcript → Emergency Detection → 
Interrupt Conversation → Emergency Response Protocol
```

## Performance Targets

### Latency Goals
- **Audio Chunk Processing**: <50ms
- **Voice Activity Detection**: <100ms
- **Emergency Detection**: <200ms
- **AI Response Initiation**: <300ms
- **End-to-End Conversation Latency**: <800ms

### Quality Metrics
- **Audio Quality**: 16kHz, 16-bit, mono
- **Transcription Accuracy**: >95% for medical terms
- **Emergency Detection Accuracy**: >99% precision, >95% recall
- **Conversation Completion Rate**: >90%

## Implementation Timeline

### Phase 1: Foundation (Weeks 1-2)
- ✅ Fix audio format issues (COMPLETED)
- ✅ Enhance TTS/STT services (COMPLETED)
- 🔧 Implement WebSocket conversation endpoint
- 🔧 Add client-side VAD

### Phase 2: ElevenLabs Integration (Weeks 3-4)
- 🔧 Set up ElevenLabs Conversational AI
- 🔧 Create hybrid conversation orchestrator
- 🔧 Implement medical context injection

### Phase 3: Real-Time Features (Weeks 5-6)
- 🔧 Build conversation state management
- 🔧 Add interruption support
- 🔧 Implement emergency detection

### Phase 4: UI/UX (Weeks 7-8)
- 🔧 Create conversational UI components
- 🔧 Add real-time visualizations
- 🔧 Implement emergency response UI

### Phase 5: Testing & Optimization (Weeks 9-10)
- 🔧 Performance optimization
- 🔧 User testing and feedback
- 🔧 Production deployment

## Risk Mitigation

### Technical Risks
1. **ElevenLabs API Limitations**: Fallback to current TTS/STT approach
2. **WebSocket Stability**: Implement automatic reconnection
3. **Audio Quality Issues**: Multiple codec support and quality adaptation
4. **Latency Problems**: Optimize audio chunk sizes and processing

### Medical Safety Risks
1. **False Emergency Detection**: Implement confidence thresholds and human review
2. **Missed Emergencies**: Multiple detection methods and escalation protocols
3. **Medical Accuracy**: Maintain TxAgent integration for medical knowledge
4. **Privacy Concerns**: End-to-end encryption and secure data handling

## Success Metrics

### User Experience
- **Conversation Completion Rate**: >90%
- **User Satisfaction**: >4.5/5 rating
- **Emergency Response Time**: <30 seconds
- **Medical Query Accuracy**: >95%

### Technical Performance
- **System Uptime**: >99.9%
- **Audio Quality Score**: >4.0/5
- **Response Latency**: <800ms average
- **Error Rate**: <1%

## Conclusion

This enhanced conversational AI upgrade plan leverages the existing robust infrastructure while adding cutting-edge conversational capabilities. By combining ElevenLabs' conversational AI with TxAgent's medical knowledge and the comprehensive medical profile system, we can create a truly intelligent medical assistant that provides natural, safe, and personalized healthcare conversations.

The phased approach ensures each component is thoroughly tested before integration, while the hybrid architecture provides both innovation and reliability. The result will be a state-of-the-art conversational health assistant that transforms how users interact with medical AI.