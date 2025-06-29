# Agent Awareness Plan: Enabling Intelligent Symptom Tracking

This document outlines the plan for implementing agent awareness across the three components of our medical application ecosystem:

1. **TxAgent Container** - The AI agent running in RunPod
2. **Backend Server** - Express.js API server
3. **Frontend Expo App** - Mobile client application

## Overview

The goal is to enable a natural, conversational flow where the AI can:
- Recognize user intent to log symptoms
- Extract symptom details from conversation
- Save symptoms to the database
- Retrieve symptom history
- Present symptom trends and patterns
- Make recommendations based on symptom history

## Current Architecture

Currently, the system operates with:
- **TxAgent Container**: Processes queries and returns responses
- **Backend**: Routes requests, manages authentication, and handles database operations
- **Frontend**: Presents UI and sends user queries

The missing piece is the ability for the AI to recognize when a user wants to log a symptom and then take appropriate action.

## Implementation Strategy

### 1. TxAgent Container Enhancements

#### A. Intent Recognition System

Add a function to detect when users are trying to log symptoms:

```python
def detect_symptom_logging_intent(query, conversation_history):
    """
    Detect if the user is trying to log a symptom.
    Returns (intent_detected, confidence, extracted_symptom_data)
    """
    # Implement intent recognition logic
    # This could use keyword matching, regex patterns, or a small classifier
    
    symptom_logging_patterns = [
        r"log (a|my) symptom",
        r"record (a|my) symptom",
        r"i('ve| have) been experiencing",
        r"i('m| am) having (a|an)",
        # More patterns...
    ]
    
    # Check for direct matches
    for pattern in symptom_logging_patterns:
        if re.search(pattern, query.lower()):
            return True, 0.9, extract_symptom_details(query, conversation_history)
    
    # More sophisticated detection logic...
    
    return False, 0.0, None
```

#### B. Symptom Extraction Function

```python
def extract_symptom_details(query, conversation_history):
    """
    Extract symptom details from the conversation.
    Returns a structured symptom object.
    """
    # Use NER or pattern matching to extract:
    # - Symptom name
    # - Duration
    # - Severity
    # - Location
    # - Triggers
    # - Associated symptoms
    
    # For complex cases, use the LLM itself to extract structured data
    
    return {
        "symptom_name": extracted_name,
        "duration_hours": extracted_duration,
        "severity": extracted_severity,
        "location": extracted_location,
        "triggers": extracted_triggers,
        "description": extracted_description
    }
```

#### C. Database Action Endpoints

Add new endpoints to the TxAgent container:

```python
@app.post("/agent-action/save-symptom")
async def save_symptom(request: Request):
    """Save a symptom to the user's profile"""
    try:
        # Get authorization header
        authorization = request.headers.get("Authorization")
        if not authorization:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authorization header missing"}
            )
        
        # Extract and validate token
        token = auth_service.extract_token_from_header(authorization)
        user_id, _ = auth_service.validate_token_and_get_user(token)
        
        # Get authenticated client
        client = auth_service.get_authenticated_client(token)
        
        # Parse request body
        data = await request.json()
        symptom_data = data.get("symptom_data", {})
        
        # Validate symptom data
        if not symptom_data.get("symptom_name"):
            return JSONResponse(
                status_code=400,
                content={"detail": "symptom_name is required"}
            )
        
        # Insert into database
        result = client.table("user_symptoms").insert({
            "user_id": user_id,
            "symptom_name": symptom_data.get("symptom_name"),
            "severity": symptom_data.get("severity"),
            "description": symptom_data.get("description"),
            "triggers": symptom_data.get("triggers"),
            "duration_hours": symptom_data.get("duration_hours"),
            "location": symptom_data.get("location")
        }).execute()
        
        if result.error:
            raise Exception(f"Database error: {result.error.message}")
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Symptom logged successfully",
                "symptom_id": result.data[0]["id"] if result.data else None
            }
        )
    
    except Exception as e:
        logger.error(f"Error saving symptom: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Failed to save symptom: {str(e)}"}
        )
```

```python
@app.get("/agent-action/get-symptoms")
async def get_symptoms(request: Request):
    """Get user's symptom history"""
    try:
        # Authentication logic (same as above)
        authorization = request.headers.get("Authorization")
        token = auth_service.extract_token_from_header(authorization)
        user_id, _ = auth_service.validate_token_and_get_user(token)
        client = auth_service.get_authenticated_client(token)
        
        # Get query parameters
        limit = request.query_params.get("limit", "10")
        symptom_name = request.query_params.get("symptom_name")
        
        # Build query
        query = client.table("user_symptoms").select("*").eq("user_id", user_id)
        
        if symptom_name:
            query = query.eq("symptom_name", symptom_name)
        
        # Execute query
        result = query.order("created_at", {"ascending": False}).limit(int(limit)).execute()
        
        if result.error:
            raise Exception(f"Database error: {result.error.message}")
        
        return JSONResponse(
            status_code=200,
            content={
                "symptoms": result.data,
                "count": len(result.data)
            }
        )
    
    except Exception as e:
        logger.error(f"Error retrieving symptoms: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Failed to retrieve symptoms: {str(e)}"}
        )
```

#### D. Chat Flow Enhancement

Modify the main chat handler to detect symptom logging intent and take appropriate actions:

```python
@app.post("/chat")
async def chat(request: Request):
    # Existing chat logic...
    
    # After processing the query with the LLM but before returning the response:
    intent_detected, confidence, symptom_data = detect_symptom_logging_intent(query, conversation_history)
    
    if intent_detected and confidence > 0.7:
        # We detected the user wants to log a symptom
        if symptom_data and symptom_data.get("symptom_name"):
            # We have enough data to log the symptom
            try:
                # Save the symptom
                save_result = await save_symptom_internal(request.headers.get("Authorization"), symptom_data)
                
                if save_result.get("success"):
                    # Modify the response to acknowledge the symptom was logged
                    response_text = f"I've logged your {symptom_data['symptom_name']} symptom. {response_text}"
                    
                    # Add action metadata to the response
                    response_metadata = {
                        "action_taken": "symptom_logged",
                        "symptom_id": save_result.get("symptom_id"),
                        "symptom_name": symptom_data.get("symptom_name")
                    }
                else:
                    # Inform the user of the failure
                    response_text = f"I tried to log your {symptom_data['symptom_name']} symptom, but encountered an issue. {response_text}"
            except Exception as e:
                logger.error(f"Error in symptom logging flow: {str(e)}")
                # Continue with normal response
        else:
            # We need more information - modify response to ask for details
            response_text = "It sounds like you want to log a symptom. Could you provide more details about what you're experiencing? " + response_text
    
    # Continue with normal response flow...
```

### 2. Backend Server Enhancements

#### A. New Proxy Endpoints

Add endpoints to proxy requests to the TxAgent container's agent-action endpoints:

```javascript
// In backend/routes/agentActions.js

import express from 'express';
import { verifyToken } from '../middleware/auth.js';
import { errorLogger } from '../agent_utils/shared/logger.js';
import { AgentService } from '../agent_utils/core/agentService.js';

export function createAgentActionsRouter(supabaseClient) {
  const router = express.Router();
  router.use(verifyToken);
  
  const agentService = new AgentService(supabaseClient);
  
  // Proxy endpoint for saving symptoms
  router.post('/save-symptom', async (req, res) => {
    const userId = req.userId;
    
    try {
      // Get active agent
      const agent = await agentService.getActiveAgent(userId);
      
      if (!agent || !agent.session_data?.runpod_endpoint) {
        return res.status(503).json({
          error: 'TxAgent service is not available',
          code: 'TXAGENT_SERVICE_UNAVAILABLE'
        });
      }
      
      // Forward request to TxAgent
      const txAgentUrl = agent.session_data.runpod_endpoint.replace(/\/+$/, '');
      const response = await fetch(`${txAgentUrl}/agent-action/save-symptom`, {
        method: 'POST',
        headers: {
          'Authorization': req.headers.authorization,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(req.body)
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`TxAgent responded with status ${response.status}: ${errorText}`);
      }
      
      const data = await response.json();
      res.json(data);
      
    } catch (error) {
      errorLogger.error('Failed to save symptom via agent action', error, {
        userId,
        component: 'AgentActions'
      });
      
      res.status(500).json({
        error: 'Failed to save symptom',
        details: error.message
      });
    }
  });
  
  // Proxy endpoint for getting symptoms
  router.get('/get-symptoms', async (req, res) => {
    const userId = req.userId;
    
    try {
      // Get active agent
      const agent = await agentService.getActiveAgent(userId);
      
      if (!agent || !agent.session_data?.runpod_endpoint) {
        return res.status(503).json({
          error: 'TxAgent service is not available',
          code: 'TXAGENT_SERVICE_UNAVAILABLE'
        });
      }
      
      // Forward request to TxAgent
      const txAgentUrl = agent.session_data.runpod_endpoint.replace(/\/+$/, '');
      const queryParams = new URLSearchParams(req.query).toString();
      const response = await fetch(`${txAgentUrl}/agent-action/get-symptoms?${queryParams}`, {
        headers: {
          'Authorization': req.headers.authorization
        }
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`TxAgent responded with status ${response.status}: ${errorText}`);
      }
      
      const data = await response.json();
      res.json(data);
      
    } catch (error) {
      errorLogger.error('Failed to get symptoms via agent action', error, {
        userId,
        component: 'AgentActions'
      });
      
      res.status(500).json({
        error: 'Failed to get symptoms',
        details: error.message
      });
    }
  });
  
  return router;
}
```

#### B. Update Medical Consultation Endpoint

Enhance the medical consultation endpoint to include symptom tracking capabilities:

```javascript
// In backend/routes/medicalConsultation.js

// Add to the existing medical-consultation endpoint:
router.post('/medical-consultation', async (req, res) => {
  // Existing code...
  
  // Add to the TxAgent request body:
  const requestBody = {
    query: augmentedQuery,
    history: context?.conversation_history || [],
    top_k: 5,
    temperature: 0.7,
    stream: false,
    context: {
      ...context,
      // Add flag to enable agent actions
      enable_agent_actions: true,
      // Add available actions
      available_actions: ['save_symptom', 'get_symptoms']
    }
  };
  
  // Rest of the existing code...
});
```

#### C. Mount New Router

```javascript
// In backend/routes/index.js

import { createAgentActionsRouter } from './agentActions.js';

export function setupRoutes(app, supabaseClient) {
  // Existing code...
  
  const agentActionsRouter = createAgentActionsRouter(supabaseClient);
  app.use('/api/agent-actions', agentActionsRouter);
  
  // Rest of the existing code...
}
```

### 3. Frontend Expo App Enhancements

#### A. Chat Context Provider

Enhance the chat context to handle agent actions:

```javascript
// In frontend/src/contexts/ChatContext.js

export const ChatProvider = ({ children }) => {
  // Existing state...
  const [agentActions, setAgentActions] = useState([]);
  
  // Handle agent actions in the response
  const processAgentActions = useCallback((response) => {
    if (response.agent_actions && Array.isArray(response.agent_actions)) {
      setAgentActions(response.agent_actions);
      
      // Process each action
      response.agent_actions.forEach(action => {
        switch (action.type) {
          case 'symptom_logged':
            // Show toast or notification
            toast.success(`Symptom logged: ${action.data.symptom_name}`);
            break;
          case 'symptoms_retrieved':
            // Update UI to show symptom history
            // This could be a modal, a new screen, or inline in the chat
            break;
          // Other action types...
        }
      });
    }
  }, []);
  
  // Modify sendMessage to handle agent actions
  const sendMessage = useCallback(async (message) => {
    // Existing code...
    
    try {
      const response = await api.post('/api/medical-consultation', {
        query: message,
        context: {
          conversation_history: recentMessages,
          user_profile: userProfile,
          // Enable agent actions
          enable_agent_actions: true
        },
        // Other parameters...
      });
      
      // Process any agent actions in the response
      processAgentActions(response.data);
      
      // Rest of existing code...
    } catch (error) {
      // Error handling...
    }
  }, [/* existing dependencies */, processAgentActions]);
  
  // Rest of the existing code...
};
```

#### B. Symptom History Component

Create a component to display symptom history:

```javascript
// In frontend/src/components/SymptomHistory.js

import React from 'react';
import { View, Text, FlatList, StyleSheet } from 'react-native';

export const SymptomHistory = ({ symptoms, symptomName }) => {
  return (
    <View style={styles.container}>
      <Text style={styles.title}>
        {symptomName ? `${symptomName} History` : 'Symptom History'}
      </Text>
      
      {symptoms.length === 0 ? (
        <Text style={styles.emptyText}>No symptoms recorded yet</Text>
      ) : (
        <FlatList
          data={symptoms}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <View style={styles.symptomItem}>
              <View style={styles.header}>
                <Text style={styles.symptomName}>{item.symptom_name}</Text>
                <Text style={styles.date}>
                  {new Date(item.created_at).toLocaleDateString()} {new Date(item.created_at).toLocaleTimeString()}
                </Text>
              </View>
              
              <View style={styles.details}>
                {item.severity && (
                  <View style={styles.detailItem}>
                    <Text style={styles.detailLabel}>Severity:</Text>
                    <Text style={styles.detailValue}>{item.severity}/10</Text>
                  </View>
                )}
                
                {item.duration_hours && (
                  <View style={styles.detailItem}>
                    <Text style={styles.detailLabel}>Duration:</Text>
                    <Text style={styles.detailValue}>{item.duration_hours} hours</Text>
                  </View>
                )}
                
                {item.location && (
                  <View style={styles.detailItem}>
                    <Text style={styles.detailLabel}>Location:</Text>
                    <Text style={styles.detailValue}>{item.location}</Text>
                  </View>
                )}
              </View>
              
              {item.description && (
                <Text style={styles.description}>{item.description}</Text>
              )}
            </View>
          )}
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    padding: 16,
    backgroundColor: '#fff',
    borderRadius: 12,
    marginVertical: 8,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 12,
    color: '#2D3748',
  },
  emptyText: {
    textAlign: 'center',
    color: '#718096',
    marginVertical: 16,
  },
  symptomItem: {
    padding: 12,
    backgroundColor: '#F7FAFC',
    borderRadius: 8,
    marginBottom: 8,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  symptomName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#2D3748',
  },
  date: {
    fontSize: 12,
    color: '#718096',
  },
  details: {
    marginBottom: 8,
  },
  detailItem: {
    flexDirection: 'row',
    marginBottom: 4,
  },
  detailLabel: {
    fontSize: 14,
    color: '#4A5568',
    width: 80,
  },
  detailValue: {
    fontSize: 14,
    color: '#2D3748',
    fontWeight: '500',
  },
  description: {
    fontSize: 14,
    color: '#4A5568',
    fontStyle: 'italic',
  },
});
```

#### C. Agent Action Hooks

Create a custom hook to handle agent actions:

```javascript
// In frontend/src/hooks/useAgentActions.js

import { useState, useCallback } from 'react';
import { api } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';

export const useAgentActions = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const saveSymptom = useCallback(async (symptomData) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.post('/api/agent-actions/save-symptom', {
        symptom_data: symptomData
      });
      
      return response.data;
    } catch (err) {
      setError(err.message || 'Failed to save symptom');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);
  
  const getSymptoms = useCallback(async (params = {}) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.get('/api/agent-actions/get-symptoms', { params });
      return response.data;
    } catch (err) {
      setError(err.message || 'Failed to get symptoms');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);
  
  return {
    saveSymptom,
    getSymptoms,
    loading,
    error
  };
};
```

## Communication Flow

1. **User Initiates Symptom Logging**:
   - User: "I'd like to log a symptom"
   - TxAgent: Detects intent, asks for details
   - User: "It's the same headache"
   - TxAgent: Extracts symptom name, checks history

2. **TxAgent Saves Symptom**:
   - TxAgent calls internal function to save symptom
   - Function makes request to `/agent-action/save-symptom` endpoint
   - Request includes JWT for authentication
   - Symptom is saved to database with user_id from JWT

3. **TxAgent Retrieves History**:
   - User: "Show me my headache history"
   - TxAgent calls internal function to get symptoms
   - Function makes request to `/agent-action/get-symptoms?symptom_name=headache` endpoint
   - TxAgent formats symptom history into human-readable response

## Implementation Phases

### Phase 1: Basic Symptom Logging

1. Implement TxAgent container endpoints
2. Add backend proxy endpoints
3. Test with direct API calls
4. Implement basic intent detection in TxAgent

### Phase 2: Enhanced Conversation Flow

1. Improve intent detection with more patterns
2. Add symptom extraction from natural language
3. Implement follow-up questions for missing details
4. Add symptom history retrieval and formatting

### Phase 3: Frontend Integration

1. Update Expo app to handle agent actions
2. Add UI components for symptom history
3. Implement notifications for successful logging
4. Add symptom tracking visualizations

## Testing Strategy

1. **Unit Tests**:
   - Test intent detection with various phrasings
   - Test symptom extraction from different conversation patterns
   - Test database operations with mock JWT tokens

2. **Integration Tests**:
   - Test end-to-end flow from user input to database storage
   - Test retrieval and formatting of symptom history
   - Test error handling and recovery

3. **User Testing**:
   - Test with real conversations to ensure natural flow
   - Verify symptom details are correctly extracted
   - Ensure history is presented in a useful format

## Conclusion

This agent awareness implementation will enable a more natural, conversational approach to symptom tracking. By allowing the AI to recognize intent, extract relevant details, and take appropriate actions, we can create a more seamless user experience that feels like talking to a knowledgeable healthcare assistant rather than filling out forms.

The implementation leverages the existing authentication infrastructure and database schema, ensuring that all actions respect user data boundaries through Row Level Security.