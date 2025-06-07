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

from embedder import Embedder
from llm import LLMHandler
from auth import get_user_id, get_auth_token, validate_token
from utils import request_logger, log_request

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

# Define request and response models
class DocumentRequest(BaseModel):
    file_path: str
    metadata: Dict[str, Any] = {}

class JobResponse(BaseModel):
    job_id: str
    status: str
    chunk_count: Optional[int] = None
    document_ids: List[str] = []
    error: Optional[str] = None
    message: str

class ChatRequest(BaseModel):
    query: str
    history: List[Dict[str, str]] = []
    top_k: int = 5
    temperature: float = 0.7
    stream: bool = False

class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]] = []
    status: str = "success"

class HealthResponse(BaseModel):
    status: str = "healthy"
    model: str = os.getenv("MODEL_NAME", "dmis-lab/biobert-v1.1")
    device: str = os.getenv("DEVICE", "cuda")
    version: str = "1.0.0"

# Middleware to log all requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Extract user info from Authorization header if present
    user_context = None
    auth_header = request.headers.get("Authorization")
    
    logger.info(f"🚀 REQUEST START: {request.method} {request.url.path}")
    logger.info(f"🔍 Request headers: {dict(request.headers)}")
    
    if auth_header and auth_header.startswith("Bearer "):
        try:
            logger.info("🔍 Found Authorization header, attempting to validate...")
            token = auth_header.split(" ")[1]
            user_id, payload = validate_token(token)
            user_context = payload
            logger.info(f"✅ Successfully authenticated user: {user_id}")
        except Exception as e:
            logger.error(f"❌ Token validation failed in middleware: {str(e)}")
            logger.error(f"❌ Exception type: {type(e).__name__}")
            request_logger.log_auth_event("token_validation", success=False, details={"error": str(e)})
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
async def process_document_task(job_id: str, file_path: str, metadata: Dict[str, Any], user_id: str, jwt: str):
    """Background task to process and embed a document."""
    request_logger.log_system_event("background_task_start", {
        "job_id": job_id,
        "file_path": file_path,
        "user_id": user_id
    })
    
    try:
        # Update job status to processing
        await embedder.update_job_status(job_id, "processing")
        
        # Process document
        document_chunks = embedder.process_document(file_path, metadata, jwt)
        
        if not document_chunks:
            await embedder.update_job_status(
                job_id,
                "failed",
                error="No content extracted from document"
            )
            request_logger.log_system_event("background_task_failed", {
                "job_id": job_id,
                "error": "No content extracted"
            }, level="error")
            return
        
        # Store embeddings
        document_ids = embedder.store_embeddings(document_chunks, user_id, jwt)
        
        # Update job with success status and document IDs
        await embedder.update_job_status(
            job_id,
            "completed",
            chunk_count=len(document_chunks),
            document_ids=document_ids
        )
        
        request_logger.log_system_event("background_task_success", {
            "job_id": job_id,
            "chunks_processed": len(document_chunks),
            "document_ids_created": len(document_ids)
        })
        
    except Exception as e:
        await embedder.update_job_status(
            job_id,
            "failed",
            error=str(e)
        )
        request_logger.log_system_event("background_task_failed", {
            "job_id": job_id,
            "error": str(e)
        }, level="error")

# API Endpoints
@app.post("/embed", response_model=JobResponse)
@log_request("/embed")
async def embed_document(
    request: DocumentRequest,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None)
):
    """
    Embed a document from Supabase Storage.
    
    This endpoint processes a document, extracts text, and creates embeddings.
    The document must exist in Supabase Storage and be accessible by the user.
    """
    logger.info(f"🚀 EMBED REQUEST: {request.file_path}")
    
    try:
        # Validate JWT and get user ID
        token = get_auth_token(authorization)
        user_id, user_payload = validate_token(token)
        
        logger.info(f"✅ Embed request authenticated for user: {user_id}")
        
        request_logger.log_auth_event("embed_request", user_context=user_payload, success=True, details={
            "file_path": request.file_path,
            "metadata_keys": list(request.metadata.keys())
        })
        
        # Create job record
        job_id = str(uuid.uuid4())
        await embedder.create_embedding_job(
            job_id,
            request.file_path,
            user_id
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
        logger.error(f"❌ HTTP error in embed endpoint: {e.detail}")
        request_logger.log_auth_event("embed_request", success=False, details={"error": e.detail})
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in embed endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.get("/embedding-jobs/{job_id}", response_model=JobResponse)
@log_request("/embedding-jobs")
async def get_job_status(
    job_id: str,
    user_id: str = Depends(get_user_id)
):
    """
    Get the status of an embedding job.
    """
    logger.info(f"🚀 JOB STATUS REQUEST: {job_id} for user {user_id}")
    
    try:
        job = await embedder.get_job_status(job_id, user_id)
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
        # Validate JWT and get user ID
        token = get_auth_token(authorization)
        user_id, user_payload = validate_token(token)
        
        logger.info(f"✅ Chat request authenticated for user: {user_id}")
        
        request_logger.log_auth_event("chat_request", user_context=user_payload, success=True, details={
            "query_length": len(request.query),
            "top_k": request.top_k,
            "temperature": request.temperature
        })
        
        # Perform similarity search
        similar_docs = embedder.similarity_search(
            query=request.query,
            user_id=user_id,
            top_k=request.top_k,
            jwt=token
        )
        
        if not similar_docs:
            return ChatResponse(
                response="I couldn't find any relevant information to answer your question.",
                sources=[],
                status="no_results"
            )
        
        # Generate response using LLM if available
        if llm_handler:
            response = await llm_handler.generate_response(
                query=request.query,
                context=similar_docs,
                temperature=request.temperature
            )
        else:
            # Fallback response if LLM not available
            response = f"Based on the documents I found, here's relevant information: {similar_docs[0]['content'][:200]}..."
        
        # Format sources for response
        sources = [
            {
                "content": doc["content"][:200] + "...",
                "metadata": doc["metadata"],
                "similarity": doc["similarity"]
            } 
            for doc in similar_docs
        ]
        
        request_logger.log_performance_metric("chat_response", time.time(), user_context=user_payload, metadata={
            "sources_found": len(sources),
            "response_length": len(response)
        })
        
        return ChatResponse(
            response=response,
            sources=sources
        )
    except HTTPException as e:
        logger.error(f"❌ HTTP error in chat endpoint: {e.detail}")
        request_logger.log_auth_event("chat_request", success=False, details={"error": e.detail})
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

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

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check if the service is healthy."""
    logger.info("🚀 HEALTH CHECK REQUEST")
    request_logger.log_system_event("health_check", {"status": "healthy"})
    return HealthResponse()

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    request_logger.log_system_event("server_start", {
        "host": host,
        "port": port,
        "debug": debug
    })
    
    uvicorn.run("main:app", host=host, port=port, reload=debug)