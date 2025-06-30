import os
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Header, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv
import uuid
import time
import psutil
import torch
import json
from datetime import datetime

from embedder import Embedder
from llm import LLMHandler

# Import from centralized auth service
from core.auth_service import auth_service, get_user_id, get_auth_token, validate_token
from core.logging import request_logger, log_request

# Import Agent Overhaul components
from conversation_engine import conversation_engine
from database_manager import database_manager

# Import legacy agent actions for backward compatibility
from agent_actions import agent_actions

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("txagent")

# Log system startup
request_logger.log_system_event("startup", {
    "model": os.getenv("MODEL_NAME", "dmis-lab/biobert-v1.1"),
    "device": os.getenv("DEVICE", "cuda"),
    "port": os.getenv("PORT", "8000"),
    "log_level": os.getenv("LOG_LEVEL", "INFO"),
    "agent_awareness": True,
    "phase": "3.0",
    "conversation_engine": True,
    "simple_intent_detection": True
})

# Initialize FastAPI app
app = FastAPI(
    title="TxAgent Hybrid Container",
    description="Medical RAG Vector Uploader with BioBERT embeddings, chat capabilities, and conversational health tracking engine",
    version="1.3.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
try:
    embedder = Embedder()
    request_logger.log_system_event("model_load", {"status": "success",  "model": "BioBERT"})
except Exception as e:
    request_logger.log_system_event("model_load", {"status": "failed", "error": str(e)}, level="error")
    raise

try:
    llm_handler = LLMHandler()
    request_logger.log_system_event("model_load", {"status": "success", "model": "OpenAI"})
except Exception as e:
    request_logger.log_system_event("model_load", {"status": "failed", "error": str(e)}, level="warning")
    llm_handler = None

# Track startup time for uptime calculation
startup_time = time.time()

# Define request and response models
class DocumentRequest(BaseModel):
    file_path: str
    metadata: Dict[str, Any] = {}

class EmbedRequest(BaseModel):
    text: str = Field(..., description="Text to generate BioBERT embedding for")
    normalize: bool = Field(True, description="Whether to normalize the embedding vector")

class EmbedResponse(BaseModel):
    embedding: List[float] = Field(..., description="768-dimensional BioBERT embedding")
    dimensions: int = Field(768, description="Number of dimensions in the embedding")
    model: str = Field("BioBERT", description="Model used for embedding generation")
    processing_time: int = Field(..., description="Processing time in milliseconds")

class JobResponse(BaseModel):
    job_id: str
    status: str
    chunk_count: Optional[int] = None
    document_ids: List[str] = []
    error: Optional[str] = None
    message: str

class ChatContext(BaseModel):
    """Context object containing user profile and conversation history"""
    user_profile: Optional[Dict[str, Any]] = Field(None, description="User's medical profile and personal information")
    conversation_history: Optional[List[Dict[str, str]]] = Field(None, description="Previous conversation messages")

class ChatRequest(BaseModel):
    query: str = Field(..., description="User's medical question or query")
    context: Optional[ChatContext] = Field(None, description="User context including profile and conversation history")
    top_k: int = Field(5, description="Number of similar documents to retrieve")
    temperature: float = Field(0.7, description="Temperature for response generation")
    stream: bool = Field(False, description="Whether to stream the response")
    tracking_session_id: Optional[str] = Field(None, description="ID of active tracking session to continue")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Generated response to the query")
    sources: List[Dict[str, Any]] = Field(default=[], description="Source documents used for the response")
    processing_time: Optional[int] = Field(None, description="Processing time in milliseconds")
    model: str = Field("Symptom Savior", description="Model used for processing")
    tokens_used: Optional[int] = Field(None, description="Number of tokens used in processing")
    status: str = Field("success", description="Status of the request")
    agent_action: Optional[Dict[str, Any]] = Field(None, description="Agent action taken if any")
    intent_detected: Optional[Dict[str, Any]] = Field(None, description="Intent detection results")
    conversation_analysis: Optional[Dict[str, Any]] = Field(None, description="Conversation analysis")
    tracking_session_id: Optional[str] = Field(None, description="ID of tracking session if active")

class AgentSessionRequest(BaseModel):
    session_data: Dict[str, Any] = {}

class AgentSessionResponse(BaseModel):
    id: str
    user_id: str
    status: str
    session_data: Dict[str, Any]
    created_at: str
    message: str = "Agent session created successfully"

class HealthResponse(BaseModel):
    status: str = "healthy"
    model: str = os.getenv("MODEL_NAME", "dmis-lab/biobert-v1.1")
    device: str = os.getenv("DEVICE", "cuda")
    version: str = "1.3.0"
    uptime: Optional[int] = None
    memory_usage: Optional[str] = None

# Mock request class for agent actions
class MockRequest:
    def __init__(self, headers, json_data=None, query_params=None):
        self.headers = headers
        self._json_data = json_data or {}
        self.query_params = query_params or {}
    
    async def json(self):
        return self._json_data

# Middleware to log all requests using centralized auth service
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Extract user info from Authorization header if present using centralized auth service
    user_context = None
    auth_header = request.headers.get("Authorization")
    
    logger.info(f"🚀 REQUEST START: {request.method} {request.url.path}")
    
    if auth_header and auth_header.startswith("Bearer "):
        try:
            logger.info("🔍 Found Authorization header, attempting to validate...")
            token = auth_header.split(" ")[1]
            user_id, payload = auth_service.validate_token_and_get_user(token)
            user_context = payload
            logger.info(f"✅ Successfully authenticated user: {user_id}")
        except Exception as e:
            logger.error(f"❌ Token validation failed in middleware: {str(e)}")
            auth_service.log_auth_event("token_validation", success=False, details={"error": str(e)})
    else:
        logger.info("ℹ️ No Authorization header found or invalid format")
    
    # Log request start
    request_logger.log_request_start(
        endpoint=f"{request.method} {request.url.path}",
        method=request.method,
        user_context=user_context,
        request_data={
            "url": str(request.url),
            "headers": dict(request.headers),
            "client": request.client.host if request.client else None
        }
    )
    
    try:
        response = await call_next(request)
        processing_time = time.time() - start_time
        
        logger.info(f"✅ REQUEST SUCCESS: {request.method} {request.url.path} - {response.status_code} ({processing_time:.2f}s)")
        
        request_logger.log_request_success(
            endpoint=f"{request.method} {request.url.path}",
            method=request.method,
            user_context=user_context,
            response_data={"status_code": response.status_code},
            processing_time=processing_time
        )
        
        return response
    except Exception as e:
        logger.error(f"❌ REQUEST ERROR: {request.method} {request.url.path} - {str(e)}")
        request_logger.log_request_error(
            endpoint=f"{request.method} {request.url.path}",
            method=request.method,
            error=e,
            user_context=user_context
        )
        raise

# Background task to process document
def process_document_task(job_id: str, file_path: str, metadata: Dict[str, Any], user_id: str, jwt: str):
    """Background task to process and embed a document."""
    request_logger.log_system_event("background_task_start", {
        "job_id": job_id,
        "file_path": file_path,
        "user_id": user_id
    })
    
    try:
        # Update job status to processing - pass JWT token
        embedder.update_job_status(job_id, "processing", jwt=jwt)
        
        # Process document
        document_chunks = embedder.process_document(file_path, metadata, jwt)
        
        if not document_chunks:
            embedder.update_job_status(
                job_id,
                "failed",
                error="No content extracted from document",
                jwt=jwt
            )
            request_logger.log_system_event("background_task_failed", {
                "job_id": job_id,
                "error": "No content extracted"
            }, level="error")
            return
        
        # Store embeddings
        document_ids = embedder.store_embeddings(document_chunks, user_id, jwt)
        
        # Update job with success status and document IDs - pass JWT token
        embedder.update_job_status(
            job_id,
            "completed",
            chunk_count=len(document_chunks),
            document_ids=document_ids,
            jwt=jwt
        )
        
        request_logger.log_system_event("background_task_success", {
            "job_id": job_id,
            "chunks_processed": len(document_chunks),
            "document_ids_created": len(document_ids)
        })
        
    except Exception as e:
        embedder.update_job_status(
            job_id,
            "failed",
            error=str(e),
            jwt=jwt
        )
        request_logger.log_system_event("background_task_failed", {
            "job_id": job_id,
            "error": str(e)
        }, level="error")

# API Endpoints
@app.get("/test-rpc")
def test_rpc(authorization: Optional[str] = Header(None)):
    token = auth_service.extract_token_from_header(authorization)
    client = auth_service.get_authenticated_client(token)
    try:
        result = client.rpc("get_active_agent", {}).execute()
        return {"data": result.data}
    except Exception as e:
        return {"error": str(e)}

# Agent Action Endpoints for backward compatibility
@app.post("/agent-action/save-symptom")
async def save_symptom_endpoint(request: Request):
    """Save a symptom to the user's profile."""
    logger.info("🚀 AGENT_ACTION: Save symptom endpoint called")
    return await agent_actions.save_symptom(request)

@app.get("/agent-action/get-symptoms")
async def get_symptoms_endpoint(request: Request):
    """Get user's symptom history."""
    logger.info("🚀 AGENT_ACTION: Get symptoms endpoint called")
    return await agent_actions.get_symptoms(request)

@app.get("/agent-action/symptom-summary")
async def get_symptom_summary_endpoint(request: Request):
    """Get user's symptom summary and patterns."""
    logger.info("🚀 AGENT_ACTION: Get symptom summary endpoint called")
    return await agent_actions.get_symptom_summary(request)

@app.post("/embed", response_model=EmbedResponse)
@log_request("/embed")
async def embed_text(
    request: EmbedRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Generate BioBERT embedding for text.
    
    This endpoint is used by the companion app's chat flow to convert
    user queries into 768-dimensional BioBERT embeddings for similarity search.
    """
    logger.info(f"🚀 EMBED TEXT REQUEST: {request.text[:50]}...")
    
    try:
        # Validate JWT if provided (optional for embedding)
        user_context = None
        if authorization:
            token = auth_service.extract_token_from_header(authorization)
            user_id, user_payload = auth_service.validate_token_and_get_user(token)
            user_context = user_payload
            logger.info(f"✅ Embed request authenticated for user: {user_id}")
        
        # Generate embedding
        start_time = time.time()
        embedding = embedder._create_embedding(request.text)
        processing_time = int((time.time() - start_time) * 1000)
        
        # Ensure exactly 768 dimensions
        if len(embedding) != 768:
            logger.error(f"❌ Embedding dimension mismatch: {len(embedding)} != 768")
            raise HTTPException(status_code=500, detail="Invalid embedding dimensions")
        
        # Normalize if requested
        if request.normalize:
            import numpy as np
            embedding_array = np.array(embedding)
            norm = np.linalg.norm(embedding_array)
            if norm > 0:
                embedding = (embedding_array / norm).tolist()
        
        logger.info(f"✅ Generated {len(embedding)}-dimensional embedding in {processing_time}ms")
        
        return EmbedResponse(
            embedding=embedding,
            dimensions=768,
            model="BioBERT",
            processing_time=processing_time
        )
        
    except HTTPException as e:
        logger.error(f"❌ HTTP error in embed endpoint: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in embed endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Embedding generation failed: {str(e)}")

@app.post("/process-document", response_model=JobResponse)
@log_request("/process-document")
async def process_document(
    request: DocumentRequest,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None)
):
    """
    Process and embed a document from Supabase Storage.
    
    This endpoint processes a full document, extracts text, chunks it,
    and creates embeddings for storage in the vector database.
    The document must exist in Supabase Storage and be accessible by the user.
    """
    logger.info(f"🚀 PROCESS DOCUMENT REQUEST: {request.file_path}")
    
    try:
        # Validate JWT and get user ID using centralized auth service
        token = auth_service.extract_token_from_header(authorization)
        user_id, user_payload = auth_service.validate_token_and_get_user(token)
        
        logger.info(f"✅ Process document request authenticated for user: {user_id}")
        
        auth_service.log_auth_event("process_document_request", user_context=user_payload, success=True, details={
            "file_path": request.file_path,
            "metadata_keys": list(request.metadata.keys())
        })
        
        # Create job record - pass JWT token
        job_id = str(uuid.uuid4())
        embedder.create_embedding_job(
            job_id,
            request.file_path,
            user_id,
            jwt=token
        )
        
        # Schedule background task
        background_tasks.add_task(
            process_document_task,
            job_id,
            request.file_path,
            request.metadata,
            user_id,
            token
        )
        
        return JobResponse(
            job_id=job_id,
            status="pending",
            message=f"Document {request.file_path} is being processed in the background"
        )
    except HTTPException as e:
        logger.error(f"❌ HTTP error in process document endpoint: {e.detail}")
        auth_service.log_auth_event("process_document_request", success=False, details={"error": e.detail})
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in process document endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.get("/embedding-jobs/{job_id}", response_model=JobResponse)
@log_request("/embedding-jobs")
def get_job_status(
    job_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Get the status of an embedding job.
    """
    try:
        # Extract JWT and user_id using centralized auth service
        token = auth_service.extract_token_from_header(authorization)
        user_id, user_payload = auth_service.validate_token_and_get_user(token)
        
        logger.info(f"🚀 JOB STATUS REQUEST: {job_id} for user {user_id}")
        
        # Pass JWT token to embedder
        job = embedder.get_job_status(job_id, user_id, jwt=token)
        if not job:
            logger.error(f"❌ Job not found: {job_id}")
            raise HTTPException(status_code=404, detail="Job not found")
            
        return JobResponse(
            job_id=job_id,
            status=job["status"],
            chunk_count=job.get("chunk_count"),
            document_ids=job.get("document_ids", []),
            error=job.get("error"),
            message=f"Job status: {job['status']}"
        )
    except HTTPException as e:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting job status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
@log_request("/chat")
async def chat(
    request: ChatRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Generate a response based on a query and document context.
    
    This endpoint uses the conversation engine to handle health tracking
    through natural dialogue, with fallback to document search for
    general health information queries.
    """
    logger.info(f"🚀 CHAT REQUEST: {request.query[:50]}...")
    
    try:
        # Validate JWT and get user ID using centralized auth service
        token = auth_service.extract_token_from_header(authorization)
        user_id, user_payload = auth_service.validate_token_and_get_user(token)
        
        logger.info(f"✅ Chat request authenticated for user: {user_id}")
        
        # Log user context information if provided
        user_profile = None
        conversation_history = []  # Always initialize as empty list
        
        if request.context:
            user_profile = request.context.user_profile
            # Ensure conversation_history is always a list
            conversation_history = request.context.conversation_history or []
            
            if user_profile:
                logger.info(f"🔍 CHAT: User profile provided with keys: {list(user_profile.keys())}")
            if conversation_history:
                logger.info(f"🔍 CHAT: Conversation history provided with {len(conversation_history)} messages")
        else:
            logger.info("ℹ️ CHAT: No context provided - using query only")
        
        start_time = time.time()
        
        # Process with conversation engine
        result = await conversation_engine.process_message(user_id, request.query, user_profile)
        
        # Check if we need to save data to database
        if result.get("save_data"):
            save_data = result["save_data"]
            save_type = save_data["type"]
            db_data = save_data["data"]
            
            if save_type == "symptom":
                save_result = await database_manager.save_symptom(user_id, db_data, token)
            elif save_type == "treatment":
                save_result = await database_manager.save_treatment(user_id, db_data, token)
            elif save_type == "appointment":
                save_result = await database_manager.save_appointment(user_id, db_data, token)
            else:
                save_result = {"success": False, "error": "Unknown save type"}
            
            if not save_result["success"]:
                result["message"] = f"I'm sorry, there was an error saving your {save_type}: {save_result.get('error', 'Unknown error')}"
        
        # Check if we need to retrieve history
        if result.get("action_needed") == "retrieve_history":
            history_type = result.get("history_type", "all")
            history_result = await database_manager.get_user_history(user_id, history_type, token)
            
            if history_result["success"]:
                history_data = history_result["data"]
                
                # Format history data for display
                formatted_history = self._format_history_data(history_data, history_type)
                result["message"] = formatted_history
            else:
                result["message"] = f"I'm sorry, there was an error retrieving your history: {history_result.get('error', 'Unknown error')}"
        
        # For health information queries, use document search
        if not result.get("question") and not result.get("session_id") and "what" in request.query.lower():
            # This might be a health information query, try document search
            similar_docs = embedder.similarity_search(
                query=request.query,
                user_id=user_id,
                top_k=request.top_k,
                jwt=token
            )
            
            if similar_docs and llm_handler:
                # Generate response using LLM
                llm_response = await llm_handler.generate_response(
                    query=request.query,
                    context=similar_docs,
                    temperature=request.temperature,
                    user_profile=user_profile,
                    conversation_history=conversation_history
                )
                
                # Combine with conversation engine response
                result["message"] = f"{result['message']}\n\n{llm_response}"
                
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
            else:
                sources = []
        else:
            sources = []
        
        # Combine message and question for response
        final_response = result["message"]
        if result.get("question"):
            final_response += f"\n\n❓ {result['question']}"
        
        # Add summary if available
        if result.get("summary"):
            final_response += f"\n\n{result['summary']}"
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return ChatResponse(
            response=final_response,
            sources=sources,
            processing_time=processing_time,
            model="Symptom Savior",
            tokens_used=0,  # No tokens used for conversation engine
            status="success",
            tracking_session_id=result.get("session_id"),
            conversation_analysis={
                "progress": result.get("progress", 0),
                "complete": result.get("complete", False)
            }
        )
        
    except HTTPException as e:
        logger.error(f"❌ HTTP error in chat endpoint: {e.detail}")
        auth_service.log_auth_event("chat_request", success=False, details={"error": e.detail})
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

    def _format_history_data(self, history_data: Dict[str, List[Dict[str, Any]]], history_type: str) -> str:
        """Format history data for display."""
        formatted = []
        
        if history_type in ["all", "symptoms"] and history_data.get("symptoms"):
            symptoms = history_data["symptoms"]
            formatted.append(f"**Symptoms** ({len(symptoms)})")
            for i, symptom in enumerate(symptoms[:5]):  # Show top 5
                created_at = datetime.fromisoformat(symptom["created_at"].replace("Z", "+00:00"))
                formatted_date = created_at.strftime("%b %d, %Y")
                formatted.append(f"{i+1}. {symptom['symptom_name'].title()} - Severity: {symptom['severity']}/10 ({formatted_date})")
        
        if history_type in ["all", "treatments"] and history_data.get("treatments"):
            treatments = history_data["treatments"]
            formatted.append(f"\n**Treatments** ({len(treatments)})")
            for i, treatment in enumerate(treatments[:5]):  # Show top 5
                created_at = datetime.fromisoformat(treatment["created_at"].replace("Z", "+00:00"))
                formatted_date = created_at.strftime("%b %d, %Y")
                formatted.append(f"{i+1}. {treatment['name'].title()} - {treatment.get('dosage', 'No dosage')} ({formatted_date})")
        
        if history_type in ["all", "appointments"] and history_data.get("appointments"):
            appointments = history_data["appointments"]
            formatted.append(f"\n**Appointments** ({len(appointments)})")
            for i, appointment in enumerate(appointments[:5]):  # Show top 5
                visit_ts = datetime.fromisoformat(appointment["visit_ts"].replace("Z", "+00:00"))
                formatted_date = visit_ts.strftime("%b %d, %Y at %I:%M %p")
                formatted.append(f"{i+1}. {appointment['doctor_name']} - {formatted_date}")
        
        if not formatted:
            return "I don't see any health records in your history yet. You can start tracking by telling me about symptoms, treatments, or appointments."
        
        return "\n".join(formatted)

# Agent session management endpoints using centralized auth service
@app.post("/agents", response_model=AgentSessionResponse)
@log_request("/agents")
def create_agent_session(
    request: AgentSessionRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Create a new agent session for the authenticated user.
    """
    logger.info(f"🚀 CREATE AGENT SESSION REQUEST")
    
    try:
        # Validate JWT and get user ID using centralized auth service
        token = auth_service.extract_token_from_header(authorization)
        user_id, user_payload = auth_service.validate_token_and_get_user(token)
        
        logger.info(f"✅ Create agent session authenticated for user: {user_id}")
        
        # Get authenticated Supabase client using centralized auth service
        client = auth_service.get_authenticated_client(token)
        
        # Create agent session using the database function
        result = client.rpc("create_agent_session", {
            "session_data": request.session_data
        }).execute()
        
        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create agent session")
        
        agent_data = result.data[0]
        
        auth_service.log_auth_event("agent_session_created", user_context=user_payload, success=True, details={
            "agent_id": agent_data["id"],
            "session_data_keys": list(request.session_data.keys())
        })
        
        return AgentSessionResponse(
            id=agent_data["id"],
            user_id=agent_data["user_id"],
            status=agent_data["status"],
            session_data=agent_data["session_data"],
            created_at=agent_data["created_at"],
            message="Agent session created successfully"
        )
    except HTTPException as e:
        logger.error(f"❌ HTTP error in create agent session: {e.detail}")
        auth_service.log_auth_event("agent_session_created", success=False, details={"error": e.detail})
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in create agent session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating agent session: {str(e)}")

@app.get("/agents/active")
@log_request("/agents/active")
def get_active_agent(
    authorization: Optional[str] = Header(None)
):
    """
    Get the active agent session for the authenticated user.
    """
    logger.info(f"🚀 GET ACTIVE AGENT REQUEST")
    
    try:
        # Validate JWT and get user ID using centralized auth service
        token = auth_service.extract_token_from_header(authorization)
        user_id, user_payload = auth_service.validate_token_and_get_user(token)
        
        logger.info(f"✅ Get active agent authenticated for user: {user_id}")
        
        # Get authenticated Supabase client using centralized auth service
        client = auth_service.get_authenticated_client(token)
        
        # Get active agent session
        result = client.rpc("get_active_agent", {}).execute()
        
        if not result.data:
            return {"agent": None, "message": "No active agent session found"}
        
        agent_data = result.data[0]
        
        return {
            "agent": {
                "id": agent_data["id"],
                "user_id": agent_data["user_id"],
                "status": agent_data["status"],
                "session_data": agent_data["session_data"],
                "created_at": agent_data["created_at"],
                "last_active": agent_data["last_active"]
            },
            "message": "Active agent session found"
        }
    except HTTPException as e:
        logger.error(f"❌ HTTP error in get active agent: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in get active agent: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting active agent: {str(e)}")

@app.delete("/agents/{agent_id}")
@log_request("/agents/terminate")
def terminate_agent_session(
    agent_id: str,
    authorization: Optional[str] = Header(None)
):
    """
    Terminate an agent session.
    """
    logger.info(f"🚀 TERMINATE AGENT SESSION REQUEST: {agent_id}")
    
    try:
        # Validate JWT and get user ID using centralized auth service
        token = auth_service.extract_token_from_header(authorization)
        user_id, user_payload = auth_service.validate_token_and_get_user(token)
        
        logger.info(f"✅ Terminate agent session authenticated for user: {user_id}")
        
        # Get authenticated Supabase client using centralized auth service
        client = auth_service.get_authenticated_client(token)
        
        # Terminate agent session
        result = client.rpc("terminate_agent_session", {
            "agent_id": agent_id
        }).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Agent session not found or not owned by user")
        
        auth_service.log_auth_event("agent_session_terminated", user_context=user_payload, success=True, details={
            "agent_id": agent_id
        })
        
        return {"message": "Agent session terminated successfully"}
    except HTTPException as e:
        logger.error(f"❌ HTTP error in terminate agent session: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in terminate agent session: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error terminating agent session: {str(e)}")

# Test endpoints for debugging
@app.get("/test")
async def test_get():
    """Test GET endpoint."""
    logger.info("🚀 TEST GET REQUEST")
    request_logger.log_system_event("test_endpoint", {"method": "GET", "status": "success"})
    return {"message": "GET endpoint working", "timestamp": time.time()}

@app.post("/test")
async def test_post(data: Dict[str, Any] = None):
    """Test POST endpoint."""
    logger.info(f"🚀 TEST POST REQUEST: {data}")
    request_logger.log_system_event("test_endpoint", {"method": "POST", "data": data, "status": "success"})
    return {"message": "POST endpoint working", "received_data": data, "timestamp": time.time()}

@app.get("/health")
async def health_check(
    request: Request,
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    authorization: Optional[str] = Header(None)
):
    """
    Check if the service is healthy.
    
    Returns detailed health information including uptime, memory usage,
    and model status for monitoring and debugging.
    
    Optionally updates agent session status if X-Session-ID header is provided.
    """
    logger.info("🚀 HEALTH CHECK REQUEST")
    
    # Calculate uptime
    uptime_seconds = int(time.time() - startup_time)
    
    # Get memory usage
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_usage = f"{memory_info.rss / 1024 / 1024:.1f}MB"
    except:
        memory_usage = "Unknown"
    
    # Build health response
    health_data = {
        "status": "healthy",
        "model": os.getenv("MODEL_NAME", "dmis-lab/biobert-v1.1"),
        "device": os.getenv("DEVICE", "cuda"),
        "version": "1.3.0",
        "uptime": uptime_seconds,
        "memory_usage": memory_usage,
        "endpoints": [
            "/health",
            "/embed", 
            "/process-document",
            "/embedding-jobs/{id}",
            "/chat",
            "/agent-action/save-symptom",
            "/agent-action/get-symptoms",
            "/agent-action/symptom-summary"
        ],
        "capabilities": {
            "document_processing": True,
            "text_embedding": True,
            "rag_chat": True,
            "vector_storage": True,
            "gpu_available": torch.cuda.is_available(),
            "user_context_support": True,
            "conversation_history_support": True,
            "agent_awareness": True,
            "symptom_tracking": True,
            "treatment_tracking": True,
            "appointment_tracking": True,
            "conversational_loops": True,
            "simple_intent_detection": True,
            "conversation_engine": True,
            "improved_bedside_manner": True,
            "tracking_session_management": True
        }
    }
    
    # Update agent session status if session ID is provided
    if x_session_id:
        logger.info(f"🔍 HEALTH CHECK: Updating session status for {x_session_id}")
        try:
            # Try to get authenticated client if JWT is provided
            client = None
            if authorization:
                try:
                    token = auth_service.extract_token_from_header(authorization)
                    user_id, _ = auth_service.validate_token_and_get_user(token)
                    client = auth_service.get_authenticated_client(token)
                    logger.info(f"✅ HEALTH CHECK: Using authenticated client for user {user_id}")
                except Exception as e:
                    logger.warning(f"⚠️ HEALTH CHECK: JWT validation failed, using service client: {str(e)}")
            
            # Fall back to service role client if no valid JWT
            if not client:
                client = auth_service.get_authenticated_client()  # Service role
                logger.info("🔍 HEALTH CHECK: Using service role client")
            
            # Update session record
            update_data = {
                "connection_status": "connected",
                "endpoints": health_data["endpoints"],
                "capabilities": health_data["capabilities"],
                "last_health_check": "now()",
                "container_status": "running"
            }
            
            result = client.table("agent_sessions").update(update_data).eq("id", x_session_id).execute()
            
            if result.data:
                logger.info(f"✅ HEALTH CHECK: Successfully updated session {x_session_id}")
                health_data["session_updated"] = True
            else:
                logger.warning(f"⚠️ HEALTH CHECK: No session found with ID {x_session_id}")
                health_data["session_updated"] = False
                
        except Exception as e:
            logger.error(f"❌ HEALTH CHECK: Error updating session {x_session_id}: {str(e)}")
            health_data["session_update_error"] = str(e)
    else:
        logger.info("🔍 HEALTH CHECK: No session ID provided, skipping session update")
    
    request_logger.log_system_event("health_check", {
        "status": "healthy",
        "session_id": x_session_id,
        "session_updated": health_data.get("session_updated", False),
        "conversation_engine": health_data["capabilities"]["conversation_engine"],
        "simple_intent_detection": health_data["capabilities"]["simple_intent_detection"]
    })
    
    return health_data

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)