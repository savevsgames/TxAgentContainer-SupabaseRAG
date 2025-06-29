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
- **TxAgent Container**: Processes queries and returns responses with enhanced user context support
- **Full-Stack Doctor's Portal Backend**: Routes requests, manages authentication, and handles database operations
- **Expo User's App Frontend**: Presents UI and sends user queries with medical profile context
- **Doctor's Portal Document Uploader**: Document upload, search and TxAgent RAG chat interface with no user context (for RAG testing the agent). This chat endpoint should remain functional and "as is" - it is not a medical consultation chat and has no user data or context in the request.

The missing piece is the ability for the AI to recognize when a user in the expo app (frontend) wants to log a symptom and then take appropriate action.

## Phase 1: Basic Symptom Logging (Foundation) - READY FOR IMPLEMENTATION

### Phase 1 Goals
- Implement basic intent recognition for symptom logging
- Create database endpoints for symptom management
- Add proxy endpoints in backend server
- Test with direct API calls
- Establish foundation for conversational symptom tracking

### Phase 1.1: Database Schema Enhancement

First, we need to add a symptoms table to the Supabase database:

```sql
-- Add to existing migration or create new migration
CREATE TABLE IF NOT EXISTS public.user_symptoms (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  symptom_name TEXT NOT NULL,
  severity INTEGER CHECK (severity >= 1 AND severity <= 10),
  description TEXT,
  triggers TEXT[],
  duration_hours INTEGER,
  location TEXT,
  metadata JSONB DEFAULT '{}'::JSONB,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.user_symptoms ENABLE ROW LEVEL SECURITY;

-- Create RLS policy
CREATE POLICY "user_symptoms_user_isolation" ON public.user_symptoms
  FOR ALL TO authenticated
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Create indexes
CREATE INDEX IF NOT EXISTS user_symptoms_user_id_idx ON public.user_symptoms(user_id);
CREATE INDEX IF NOT EXISTS user_symptoms_created_at_idx ON public.user_symptoms(created_at);
CREATE INDEX IF NOT EXISTS user_symptoms_symptom_name_idx ON public.user_symptoms(symptom_name);
```

### Phase 1.2: TxAgent Container Enhancements

#### A. Intent Recognition System

Add a new file `hybrid-agent/intent_recognition.py`:

```python
import re
import logging
from typing import Tuple, Optional, Dict, Any, List

logger = logging.getLogger("intent_recognition")

class IntentRecognizer:
    """Recognizes user intents for symptom logging and management."""
    
    def __init__(self):
        # Patterns for symptom logging intent
        self.symptom_logging_patterns = [
            r"log (a|my|this) symptom",
            r"record (a|my|this) symptom", 
            r"save (a|my|this) symptom",
            r"track (a|my|this) symptom",
            r"i('ve| have) been experiencing",
            r"i('m| am) having (a|an)",
            r"i('ve| have) had (a|an)",
            r"i('m| am) feeling",
            r"my (head|stomach|back|chest|throat) (hurts|aches|is sore)",
            r"i have (a|an) (headache|stomachache|backache|fever|cough|rash)",
            r"i('m| am) experiencing (pain|discomfort|nausea|dizziness)",
            r"can you log",
            r"please record",
            r"add to my symptoms",
            r"note that i",
        ]
        
        # Patterns for symptom history requests
        self.history_patterns = [
            r"show (me )?my symptom history",
            r"what symptoms have i logged",
            r"my (previous|past) symptoms",
            r"symptom (log|history|record)",
            r"when did i last have",
            r"how often do i get",
            r"my (headache|pain|fever) history",
        ]
        
        # Common symptom names for extraction
        self.symptom_names = [
            "headache", "migraine", "fever", "cough", "sore throat", "nausea",
            "dizziness", "fatigue", "back pain", "chest pain", "stomach ache",
            "rash", "shortness of breath", "joint pain", "muscle ache",
            "insomnia", "anxiety", "depression", "heartburn", "constipation",
            "diarrhea", "vomiting", "runny nose", "congestion", "sneezing"
        ]
        
        # Severity indicators
        self.severity_patterns = {
            r"(very )?mild|slight|minor": 2,
            r"moderate|medium": 5,
            r"severe|intense|terrible|awful|unbearable": 8,
            r"worst|excruciating|agonizing": 10,
            r"(\d+) out of (\d+)": "extract_numeric",
            r"(\d+)/(\d+)": "extract_numeric"
        }
        
        # Duration patterns
        self.duration_patterns = {
            r"(\d+) hours?": "hours",
            r"(\d+) days?": "days", 
            r"(\d+) weeks?": "weeks",
            r"all day": 24,
            r"few hours": 3,
            r"couple hours": 2,
            r"since (morning|yesterday|last night)": "relative"
        }

    def detect_intent(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Tuple[str, float, Dict[str, Any]]:
        """
        Detect user intent from query and conversation history.
        
        Returns:
            (intent_type, confidence, extracted_data)
        """
        query_lower = query.lower()
        
        # Check for symptom logging intent
        for pattern in self.symptom_logging_patterns:
            if re.search(pattern, query_lower):
                logger.info(f"🔍 INTENT: Detected symptom logging intent with pattern: {pattern}")
                extracted_data = self._extract_symptom_data(query, conversation_history)
                return "log_symptom", 0.9, extracted_data
        
        # Check for symptom history intent
        for pattern in self.history_patterns:
            if re.search(pattern, query_lower):
                logger.info(f"🔍 INTENT: Detected symptom history intent with pattern: {pattern}")
                extracted_data = self._extract_history_request(query)
                return "get_symptom_history", 0.8, extracted_data
        
        # No specific intent detected
        return "general_chat", 0.0, {}

    def _extract_symptom_data(self, query: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        """Extract symptom details from the query and conversation history."""
        query_lower = query.lower()
        extracted = {}
        
        # Extract symptom name
        symptom_name = self._extract_symptom_name(query_lower)
        if symptom_name:
            extracted["symptom_name"] = symptom_name
        
        # Extract severity
        severity = self._extract_severity(query_lower)
        if severity:
            extracted["severity"] = severity
        
        # Extract duration
        duration = self._extract_duration(query_lower)
        if duration:
            extracted["duration_hours"] = duration
        
        # Extract location/body part
        location = self._extract_location(query_lower)
        if location:
            extracted["location"] = location
        
        # Store original description
        extracted["description"] = query
        
        logger.info(f"🔍 SYMPTOM_EXTRACT: Extracted data: {extracted}")
        return extracted

    def _extract_symptom_name(self, query_lower: str) -> Optional[str]:
        """Extract symptom name from query."""
        for symptom in self.symptom_names:
            if symptom in query_lower:
                return symptom
        
        # Try to extract from common patterns
        patterns = [
            r"i have (a|an) ([a-z ]+)",
            r"experiencing ([a-z ]+)",
            r"feeling ([a-z ]+)",
            r"my ([a-z ]+) (hurts|aches|is sore)"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query_lower)
            if match:
                potential_symptom = match.group(-1).strip()
                # Basic validation - should be 1-3 words
                if len(potential_symptom.split()) <= 3:
                    return potential_symptom
        
        return None

    def _extract_severity(self, query_lower: str) -> Optional[int]:
        """Extract severity rating from query."""
        for pattern, value in self.severity_patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                if value == "extract_numeric":
                    # Extract numeric rating like "7 out of 10" or "8/10"
                    numbers = [int(x) for x in match.groups() if x.isdigit()]
                    if len(numbers) == 2:
                        return min(10, max(1, int((numbers[0] / numbers[1]) * 10)))
                elif isinstance(value, int):
                    return value
        
        return None

    def _extract_duration(self, query_lower: str) -> Optional[int]:
        """Extract duration in hours from query."""
        for pattern, unit in self.duration_patterns.items():
            match = re.search(pattern, query_lower)
            if match:
                if unit == "hours":
                    return int(match.group(1))
                elif unit == "days":
                    return int(match.group(1)) * 24
                elif unit == "weeks":
                    return int(match.group(1)) * 24 * 7
                elif isinstance(unit, int):
                    return unit
        
        return None

    def _extract_location(self, query_lower: str) -> Optional[str]:
        """Extract body location from query."""
        body_parts = [
            "head", "forehead", "temple", "neck", "throat", "chest", "back",
            "stomach", "abdomen", "arm", "leg", "knee", "shoulder", "wrist",
            "ankle", "foot", "hand", "finger", "toe", "eye", "ear", "nose"
        ]
        
        for part in body_parts:
            if part in query_lower:
                return part
        
        return None

    def _extract_history_request(self, query: str) -> Dict[str, Any]:
        """Extract details from symptom history request."""
        query_lower = query.lower()
        extracted = {}
        
        # Check if asking for specific symptom history
        symptom_name = self._extract_symptom_name(query_lower)
        if symptom_name:
            extracted["symptom_name"] = symptom_name
        
        # Check for time range
        if "last week" in query_lower:
            extracted["days_back"] = 7
        elif "last month" in query_lower:
            extracted["days_back"] = 30
        elif "recent" in query_lower:
            extracted["days_back"] = 14
        
        return extracted
```

#### B. Agent Action Endpoints

Add a new file `hybrid-agent/agent_actions.py`:

```python
import logging
import json
from typing import Dict, Any, Optional, List
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse

from core.auth_service import auth_service
from core.logging import request_logger

logger = logging.getLogger("agent_actions")

class AgentActions:
    """Handles agent actions like saving and retrieving symptoms."""
    
    def __init__(self):
        pass

    async def save_symptom(self, request: Request) -> JSONResponse:
        """Save a symptom to the user's profile."""
        try:
            # Get authorization header
            authorization = request.headers.get("Authorization")
            if not authorization:
                logger.error("❌ SAVE_SYMPTOM: Authorization header missing")
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authorization header missing"}
                )
            
            # Extract and validate token
            token = auth_service.extract_token_from_header(authorization)
            user_id, user_payload = auth_service.validate_token_and_get_user(token)
            
            logger.info(f"🔍 SAVE_SYMPTOM: Request from user {user_id}")
            
            # Get authenticated client
            client = auth_service.get_authenticated_client(token)
            
            # Parse request body
            data = await request.json()
            symptom_data = data.get("symptom_data", {})
            
            logger.info(f"🔍 SAVE_SYMPTOM: Symptom data: {symptom_data}")
            
            # Validate symptom data
            if not symptom_data.get("symptom_name"):
                logger.error("❌ SAVE_SYMPTOM: symptom_name is required")
                return JSONResponse(
                    status_code=400,
                    content={"detail": "symptom_name is required"}
                )
            
            # Prepare data for insertion
            insert_data = {
                "user_id": user_id,
                "symptom_name": symptom_data.get("symptom_name"),
                "description": symptom_data.get("description"),
            }
            
            # Add optional fields if present
            if symptom_data.get("severity"):
                insert_data["severity"] = symptom_data.get("severity")
            if symptom_data.get("duration_hours"):
                insert_data["duration_hours"] = symptom_data.get("duration_hours")
            if symptom_data.get("location"):
                insert_data["location"] = symptom_data.get("location")
            if symptom_data.get("triggers"):
                insert_data["triggers"] = symptom_data.get("triggers")
            
            # Insert into database
            result = client.table("user_symptoms").insert(insert_data).execute()
            
            if hasattr(result, 'error') and result.error:
                logger.error(f"❌ SAVE_SYMPTOM: Database error: {result.error}")
                raise Exception(f"Database error: {result.error}")
            
            symptom_id = result.data[0]["id"] if result.data else None
            
            logger.info(f"✅ SAVE_SYMPTOM: Successfully saved symptom {symptom_id}")
            
            # Log the action
            auth_service.log_auth_event("symptom_saved", user_context=user_payload, success=True, details={
                "symptom_id": symptom_id,
                "symptom_name": symptom_data.get("symptom_name")
            })
            
            return JSONResponse(
                status_code=200,
                content={
                    "success": True,
                    "message": "Symptom logged successfully",
                    "symptom_id": symptom_id,
                    "symptom_name": symptom_data.get("symptom_name")
                }
            )
        
        except HTTPException as e:
            logger.error(f"❌ SAVE_SYMPTOM: HTTP error: {e.detail}")
            raise
        except Exception as e:
            logger.error(f"❌ SAVE_SYMPTOM: Unexpected error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"detail": f"Failed to save symptom: {str(e)}"}
            )

    async def get_symptoms(self, request: Request) -> JSONResponse:
        """Get user's symptom history."""
        try:
            # Get authorization header
            authorization = request.headers.get("Authorization")
            if not authorization:
                logger.error("❌ GET_SYMPTOMS: Authorization header missing")
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authorization header missing"}
                )
            
            # Extract and validate token
            token = auth_service.extract_token_from_header(authorization)
            user_id, user_payload = auth_service.validate_token_and_get_user(token)
            
            logger.info(f"🔍 GET_SYMPTOMS: Request from user {user_id}")
            
            # Get authenticated client
            client = auth_service.get_authenticated_client(token)
            
            # Get query parameters
            limit = int(request.query_params.get("limit", "10"))
            symptom_name = request.query_params.get("symptom_name")
            days_back = request.query_params.get("days_back")
            
            logger.info(f"🔍 GET_SYMPTOMS: Filters - limit: {limit}, symptom_name: {symptom_name}, days_back: {days_back}")
            
            # Build query
            query = client.table("user_symptoms").select("*").eq("user_id", user_id)
            
            if symptom_name:
                query = query.eq("symptom_name", symptom_name)
            
            if days_back:
                # Filter by date range
                query = query.gte("created_at", f"now() - interval '{days_back} days'")
            
            # Execute query
            result = query.order("created_at", {"ascending": False}).limit(limit).execute()
            
            if hasattr(result, 'error') and result.error:
                logger.error(f"❌ GET_SYMPTOMS: Database error: {result.error}")
                raise Exception(f"Database error: {result.error}")
            
            symptoms = result.data or []
            
            logger.info(f"✅ GET_SYMPTOMS: Retrieved {len(symptoms)} symptoms")
            
            # Log the action
            auth_service.log_auth_event("symptoms_retrieved", user_context=user_payload, success=True, details={
                "count": len(symptoms),
                "symptom_name": symptom_name
            })
            
            return JSONResponse(
                status_code=200,
                content={
                    "symptoms": symptoms,
                    "count": len(symptoms),
                    "filters": {
                        "symptom_name": symptom_name,
                        "days_back": days_back,
                        "limit": limit
                    }
                }
            )
        
        except HTTPException as e:
            logger.error(f"❌ GET_SYMPTOMS: HTTP error: {e.detail}")
            raise
        except Exception as e:
            logger.error(f"❌ GET_SYMPTOMS: Unexpected error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"detail": f"Failed to retrieve symptoms: {str(e)}"}
            )

# Global instance
agent_actions = AgentActions()
```

#### C. Enhanced Chat Endpoint

Modify `hybrid-agent/main.py` to integrate intent recognition:

```python
# Add these imports at the top
from intent_recognition import IntentRecognizer
from agent_actions import agent_actions

# Add after other service initializations
try:
    intent_recognizer = IntentRecognizer()
    request_logger.log_system_event("intent_recognition_load", {"status": "success"})
except Exception as e:
    request_logger.log_system_event("intent_recognition_load", {"status": "failed", "error": str(e)}, level="error")
    intent_recognizer = None

# Add new endpoints for agent actions
@app.post("/agent-action/save-symptom")
async def save_symptom_endpoint(request: Request):
    """Save a symptom to the user's profile."""
    return await agent_actions.save_symptom(request)

@app.get("/agent-action/get-symptoms")
async def get_symptoms_endpoint(request: Request):
    """Get user's symptom history."""
    return await agent_actions.get_symptoms(request)

# Modify the chat endpoint to include intent recognition
@app.post("/chat", response_model=ChatResponse)
@log_request("/chat")
async def chat(
    request: ChatRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Generate a response based on a query and document context.
    
    This endpoint performs similarity search to find relevant documents,
    then generates a response using an LLM based on the query and context.
    Now enhanced to utilize user profile and conversation history for personalized responses,
    and includes intent recognition for agent actions like symptom logging.
    """
    logger.info(f"🚀 CHAT REQUEST: {request.query[:50]}...")
    
    try:
        # Validate JWT and get user ID using centralized auth service
        token = auth_service.extract_token_from_header(authorization)
        user_id, user_payload = auth_service.validate_token_and_get_user(token)
        
        logger.info(f"✅ Chat request authenticated for user: {user_id}")
        
        # Log user context information if provided
        user_profile = None
        conversation_history = None
        
        if request.context:
            user_profile = request.context.user_profile
            conversation_history = request.context.conversation_history
            
            if user_profile:
                logger.info(f"🔍 CHAT: User profile provided with keys: {list(user_profile.keys())}")
            if conversation_history:
                logger.info(f"🔍 CHAT: Conversation history provided with {len(conversation_history)} messages")
        else:
            logger.info("ℹ️ CHAT: No context provided - using query only")
        
        # PHASE 1: Intent Recognition
        intent_type = "general_chat"
        intent_confidence = 0.0
        intent_data = {}
        agent_action_result = None
        
        if intent_recognizer:
            intent_type, intent_confidence, intent_data = intent_recognizer.detect_intent(
                request.query, 
                conversation_history
            )
            
            logger.info(f"🔍 INTENT: Detected '{intent_type}' with confidence {intent_confidence}")
            
            # Handle symptom logging intent
            if intent_type == "log_symptom" and intent_confidence > 0.7:
                if intent_data.get("symptom_name"):
                    # We have enough data to log the symptom
                    try:
                        # Create a mock request for the agent action
                        from fastapi import Request
                        import json
                        
                        # Save the symptom using the agent action
                        mock_request = type('MockRequest', (), {
                            'headers': {'Authorization': authorization},
                            'json': lambda: {"symptom_data": intent_data}
                        })()
                        
                        save_result = await agent_actions.save_symptom(mock_request)
                        
                        if save_result.status_code == 200:
                            result_data = json.loads(save_result.body.decode())
                            agent_action_result = {
                                "action": "symptom_logged",
                                "success": True,
                                "data": result_data
                            }
                            logger.info(f"✅ INTENT: Successfully logged symptom: {intent_data.get('symptom_name')}")
                        else:
                            agent_action_result = {
                                "action": "symptom_logging_failed", 
                                "success": False,
                                "error": "Failed to save symptom"
                            }
                            logger.error(f"❌ INTENT: Failed to log symptom")
                    except Exception as e:
                        logger.error(f"❌ INTENT: Error in symptom logging: {str(e)}")
                        agent_action_result = {
                            "action": "symptom_logging_failed",
                            "success": False, 
                            "error": str(e)
                        }
            
            # Handle symptom history intent
            elif intent_type == "get_symptom_history" and intent_confidence > 0.7:
                try:
                    # Create query parameters
                    query_params = {}
                    if intent_data.get("symptom_name"):
                        query_params["symptom_name"] = intent_data["symptom_name"]
                    if intent_data.get("days_back"):
                        query_params["days_back"] = intent_data["days_back"]
                    
                    # Create a mock request for the agent action
                    mock_request = type('MockRequest', (), {
                        'headers': {'Authorization': authorization},
                        'query_params': query_params
                    })()
                    
                    history_result = await agent_actions.get_symptoms(mock_request)
                    
                    if history_result.status_code == 200:
                        result_data = json.loads(history_result.body.decode())
                        agent_action_result = {
                            "action": "symptom_history_retrieved",
                            "success": True,
                            "data": result_data
                        }
                        logger.info(f"✅ INTENT: Successfully retrieved symptom history")
                    else:
                        agent_action_result = {
                            "action": "symptom_history_failed",
                            "success": False,
                            "error": "Failed to retrieve symptom history"
                        }
                except Exception as e:
                    logger.error(f"❌ INTENT: Error retrieving symptom history: {str(e)}")
                    agent_action_result = {
                        "action": "symptom_history_failed",
                        "success": False,
                        "error": str(e)
                    }
        
        auth_service.log_auth_event("chat_request", user_context=user_payload, success=True, details={
            "query_length": len(request.query),
            "top_k": request.top_k,
            "temperature": request.temperature,
            "has_user_profile": user_profile is not None,
            "has_conversation_history": conversation_history is not None and len(conversation_history) > 0,
            "intent_type": intent_type,
            "intent_confidence": intent_confidence,
            "agent_action_taken": agent_action_result is not None
        })
        
        start_time = time.time()
        
        # Perform similarity search - pass the JWT token string
        logger.info(f"🔍 CHAT: Calling similarity_search with JWT token")
        similar_docs = embedder.similarity_search(
            query=request.query,
            user_id=user_id,
            top_k=request.top_k,
            jwt=token  # Pass the JWT token string
        )
        
        if not similar_docs:
            base_response = "I couldn't find any relevant information to answer your question. Please make sure you have uploaded some documents first."
        else:
            # Generate response using LLM if available - now with user context
            if llm_handler:
                response = await llm_handler.generate_response(
                    query=request.query,
                    context=similar_docs,
                    temperature=request.temperature,
                    user_profile=user_profile,
                    conversation_history=conversation_history
                )
                tokens_used = len(response.split())  # Rough token estimate
                base_response = response
            else:
                # Fallback response if LLM not available
                base_response = f"Based on the documents I found, here's relevant information: {similar_docs[0]['content'][:200]}..."
                tokens_used = len(base_response.split())
        
        # Modify response based on agent actions
        final_response = base_response
        if agent_action_result:
            if agent_action_result["action"] == "symptom_logged" and agent_action_result["success"]:
                symptom_name = agent_action_result["data"].get("symptom_name", "symptom")
                final_response = f"✅ I've logged your {symptom_name} in your symptom history. {base_response}"
            elif agent_action_result["action"] == "symptom_history_retrieved" and agent_action_result["success"]:
                symptoms = agent_action_result["data"].get("symptoms", [])
                if symptoms:
                    symptom_summary = f"I found {len(symptoms)} symptom entries in your history. "
                    final_response = f"{symptom_summary}{base_response}"
                else:
                    final_response = "I didn't find any symptoms in your history yet. " + base_response
            elif not agent_action_result["success"]:
                final_response = f"I tried to help with your request but encountered an issue: {agent_action_result.get('error', 'Unknown error')}. {base_response}"
        
        # Format sources for response
        sources = [
            {
                "content": doc["content"][:200] + "...",
                "metadata": doc["metadata"],
                "similarity": doc["similarity"],
                "filename": doc.get("filename", "Unknown"),
                "chunk_id": f"chunk_{i}",
                "page": doc.get("metadata", {}).get("page")
            } 
            for i, doc in enumerate(similar_docs)
        ]
        
        processing_time = int((time.time() - start_time) * 1000)
        
        request_logger.log_performance_metric("chat_response", time.time() - start_time, user_context=user_payload, metadata={
            "sources_found": len(sources),
            "response_length": len(final_response),
            "tokens_used": tokens_used,
            "used_user_profile": user_profile is not None,
            "used_conversation_history": conversation_history is not None and len(conversation_history) > 0,
            "intent_detected": intent_type,
            "agent_action_taken": agent_action_result is not None
        })
        
        # Build response with agent action metadata
        response_data = {
            "response": final_response,
            "sources": sources,
            "processing_time": processing_time,
            "model": "BioBERT",
            "tokens_used": tokens_used,
            "status": "success"
        }
        
        # Add agent action metadata if present
        if agent_action_result:
            response_data["agent_action"] = agent_action_result
            response_data["intent_detected"] = {
                "type": intent_type,
                "confidence": intent_confidence,
                "data": intent_data
            }
        
        return ChatResponse(**response_data)
        
    except HTTPException as e:
        logger.error(f"❌ HTTP error in chat endpoint: {e.detail}")
        auth_service.log_auth_event("chat_request", success=False, details={"error": e.detail})
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")
```

### Phase 1.3: Backend Server Enhancements

Create a new file `backend/routes/agentActions.js`:

```javascript
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

Update `backend/routes/index.js`:

```javascript
import { createAgentActionsRouter } from './agentActions.js';

export function setupRoutes(app, supabaseClient) {
  // Existing code...
  
  const agentActionsRouter = createAgentActionsRouter(supabaseClient);
  app.use('/api/agent-actions', agentActionsRouter);
  
  // Rest of the existing code...
}
```

### Phase 1.4: Testing Strategy

#### A. Direct API Testing

Create test scripts to validate the new endpoints:

```bash
# Test symptom logging
curl -X POST "https://your-container-url/agent-action/save-symptom" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "symptom_data": {
      "symptom_name": "headache",
      "severity": 7,
      "duration_hours": 4,
      "location": "forehead",
      "description": "Sharp pain in forehead area"
    }
  }'

# Test symptom retrieval
curl -X GET "https://your-container-url/agent-action/get-symptoms?limit=5" \
  -H "Authorization: Bearer <jwt_token>"

# Test intent recognition via chat
curl -X POST "https://your-container-url/chat" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "I want to log a headache symptom",
    "context": {
      "user_profile": {
        "age": 30,
        "gender": "female"
      }
    }
  }'
```

#### B. Backend Proxy Testing

```bash
# Test via backend proxy
curl -X POST "https://your-backend-url/api/agent-actions/save-symptom" \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "symptom_data": {
      "symptom_name": "nausea",
      "severity": 5,
      "description": "Feeling sick after eating"
    }
  }'
```

### Phase 1.5: Success Criteria

Phase 1 will be considered successful when:

1. ✅ **Database Schema**: `user_symptoms` table created with proper RLS
2. ✅ **Intent Recognition**: System can detect "log symptom" and "get history" intents
3. ✅ **Symptom Extraction**: Basic extraction of symptom name, severity, duration
4. ✅ **Database Operations**: Can save and retrieve symptoms with user isolation
5. ✅ **API Endpoints**: Direct TxAgent endpoints work with JWT authentication
6. ✅ **Backend Proxy**: Backend can proxy requests to TxAgent container
7. ✅ **Chat Integration**: Chat endpoint can detect intents and take actions
8. ✅ **Testing**: All endpoints tested with direct API calls

### Phase 1.6: Expected User Experience

After Phase 1 implementation:

**User**: "I have a headache"
**TxAgent**: "I've logged your headache in your symptom history. Based on your medical profile and documents, headaches can be caused by various factors including stress, dehydration, or underlying conditions. Would you like me to provide some general information about headache management?"

**User**: "Show me my headache history"
**TxAgent**: "I found 3 headache entries in your history. Your most recent headache was logged 2 days ago with a severity of 7/10. Based on your pattern, you seem to experience headaches every few days. Here's some relevant information from your medical documents about headache management..."

## Phase 2: Enhanced Conversation Flow (Intelligence) - PLANNED

### Phase 2 Goals (Future Implementation)
- Improve intent detection with more sophisticated patterns
- Add symptom extraction using LLM for complex descriptions
- Implement follow-up questions for missing details
- Add symptom history analysis and trend detection
- Enhance conversation flow with natural language understanding

## Phase 3: Frontend Integration (User Experience) - PLANNED

### Phase 3 Goals (Future Implementation)
- Update Expo app to handle agent actions in chat responses
- Add UI components for symptom history visualization
- Implement notifications for successful symptom logging
- Add symptom tracking dashboards and trends
- Create symptom management workflows

## Implementation Notes

### Security Considerations
- All symptom data is protected by Row Level Security (RLS)
- JWT tokens are required for all operations
- User data is automatically isolated by user_id
- All database operations respect existing authentication patterns

### Performance Considerations
- Intent recognition uses lightweight pattern matching for Phase 1
- Database queries are optimized with proper indexes
- Symptom data is stored efficiently with JSONB for metadata
- Caching can be added for frequently accessed symptom patterns

### Scalability Considerations
- Database schema supports millions of symptom entries per user
- Intent recognition can be enhanced with ML models in future phases
- API endpoints are stateless and can be horizontally scaled
- Background processing can be added for complex symptom analysis

## Next Steps for Phase 1 Implementation

1. **Update Database Schema**: Add the `user_symptoms` table to Supabase
2. **Implement TxAgent Changes**: Add intent recognition and agent action endpoints
3. **Update Backend Server**: Add proxy endpoints for agent actions
4. **Test Integration**: Validate end-to-end flow with API testing
5. **Document API**: Update API documentation with new endpoints
6. **Monitor Performance**: Add logging and monitoring for new features

This Phase 1 implementation provides the foundation for intelligent symptom tracking while maintaining the existing architecture and security patterns. The modular approach allows for incremental enhancement in future phases.