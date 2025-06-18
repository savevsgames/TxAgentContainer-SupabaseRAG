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

from embedder import Embedder
from llm import LLMHandler

# Import from centralized auth service
from core.auth_service import auth_service, get_user_id, get_auth_token, validate_token
from core.logging import request_logger, log_request

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
    "log_level": os.getenv("LOG_LEVEL", "INFO")
})

# Initialize FastAPI app
app = FastAPI(
    title="TxAgent Hybrid Container",
    description="Medical RAG Vector Uploader with BioBERT embeddings and chat capabilities",
    version="1.0.0"
)

# Add CORS middleware with extensive logging
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
    request_logger.log_system_event("model_load", {"status": "success", "model": "BioBERT"})
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

class ChatRequest(BaseModel):
    query: str = Field(..., description="User's medical question or query")
    history: List[Dict[str, str]] = Field(default=[], description="Previous conversation history")
    top_k: int = Field(5, description="Number of similar documents to retrieve")
    temperature: float = Field(0.7, description="Temperature for response generation")
    stream: bool = Field(False, description="Whether to stream the response")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Generated response to the query")
    sources: List[Dict[str, Any]] = Field(default=[], description="Source documents used for the response")
    processing_time: Optional[int] = Field(None, description="Processing time in milliseconds")
    model: str = Field("BioBERT", description="Model used for processing")
    tokens_used: Optional[int] = Field(None, description="Number of tokens used in processing")
    status: str = Field("success", description="Status of the request")

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
    version: str = "1.0.0"
    uptime: Optional[int] = None
    memory_usage: Optional[str] = None

# Middleware to log all requests using centralized auth service
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Extract user info from Authorization header if present using centralized auth service
    user_context = None
    auth_header = request.headers.get("Authorization")
    
    logger.info(f"🚀 REQUEST START: {request.method} {request.url.path}")
    logger.info(f"🔍 Request headers: {dict(request.headers)}")
    
    if auth_header and auth_header.startswith("Bearer "):
        try:
            logger.info("🔍 Found Authorization header, attempting to validate...")
            token = auth_header.split(" ")[1]
            user_id, payload = auth_service.validate_token_and_get_user(token)
            user_context = payload
            logger.info(f"✅ Successfully authenticated user: {user_id}")
        except Exception as e:
            logger.error(f"❌ Token validation failed in middleware: {str(e)}")
            logger.error(f"❌ Exception type: {type(e).__name__}")
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
    print(f"📦 Background task started for job {job_id}")
    
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

    print("✅ Hit process-document route")

    
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
    authorization: Optional[str] = Header(None)  # Add this line
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
    
    This endpoint performs similarity search to find relevant documents,
    then generates a response using an LLM based on the query and context.
    """
    logger.info(f"🚀 CHAT REQUEST: {request.query[:50]}...")
    
    try:
        # Validate JWT and get user ID using centralized auth service
        token = auth_service.extract_token_from_header(authorization)
        user_id, user_payload = auth_service.validate_token_and_get_user(token)
        
        logger.info(f"✅ Chat request authenticated for user: {user_id}")
        
        auth_service.log_auth_event("chat_request", user_context=user_payload, success=True, details={
            "query_length": len(request.query),
            "top_k": request.top_k,
            "temperature": request.temperature
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
            return ChatResponse(
                response="I couldn't find any relevant information to answer your question. Please make sure you have uploaded some documents first.",
                sources=[],
                processing_time=int((time.time() - start_time) * 1000),
                model="BioBERT",
                tokens_used=0,
                status="no_results"
            )
        
        # Generate response using LLM if available
        if llm_handler:
            response = await llm_handler.generate_response(
                query=request.query,
                context=similar_docs,
                temperature=request.temperature
            )
            tokens_used = len(response.split())  # Rough token estimate
        else:
            # Fallback response if LLM not available
            response = f"Based on the documents I found, here's relevant information: {similar_docs[0]['content'][:200]}..."
            tokens_used = len(response.split())
        
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
            "response_length": len(response),
            "tokens_used": tokens_used
        })
        
        return ChatResponse(
            response=response,
            sources=sources,
            processing_time=processing_time,
            model="BioBERT",
            tokens_used=tokens_used,
            status="success"
        )
    except HTTPException as e:
        logger.error(f"❌ HTTP error in chat endpoint: {e.detail}")
        auth_service.log_auth_event("chat_request", success=False, details={"error": e.detail})
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

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
        "version": "1.0.0",
        "uptime": uptime_seconds,
        "memory_usage": memory_usage,
        "endpoints": [
            "/health",
            "/embed", 
            "/process-document",
            "/embedding-jobs/{id}",
            "/chat"
        ],
        "capabilities": {
            "document_processing": True,
            "text_embedding": True,
            "rag_chat": True,
            "vector_storage": True,
            "gpu_available": torch.cuda.is_available()
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
        "session_updated": health_data.get("session_updated", False)
    })
    
    return health_data