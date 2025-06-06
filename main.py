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

from embedder import Embedder
from auth import get_user_id, get_auth_token, validate_token

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("txagent")

# Initialize FastAPI app
app = FastAPI(
    title="TxAgent Hybrid Container",
    description="Medical RAG Vector Uploader with BioBERT embeddings and chat capabilities",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize embedder
embedder = Embedder()

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

# Background task to process document
async def process_document_task(job_id: str, file_path: str, metadata: Dict[str, Any], user_id: str, jwt: str):
    """Background task to process and embed a document."""
    logger.info(f"Processing document in background: {file_path} for user {user_id}")
    
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
        
        logger.info(f"Background processing complete: {len(document_ids)} chunks embedded")
    except Exception as e:
        logger.error(f"Error in background processing: {str(e)}")
        await embedder.update_job_status(
            job_id,
            "failed",
            error=str(e)
        )

# API Endpoints
@app.post("/embed", response_model=JobResponse)
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
    logger.info(f"Embedding document request received: {request.file_path}")
    
    try:
        # Validate JWT and get user ID
        token = get_auth_token(authorization)
        user_id, _ = validate_token(token)
        
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
        logger.error(f"HTTP error in embed endpoint: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Error in embed endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.get("/embedding-jobs/{job_id}", response_model=JobResponse)
async def get_job_status(
    job_id: str,
    user_id: str = Depends(get_user_id)
):
    """
    Get the status of an embedding job.
    """
    try:
        job = await embedder.get_job_status(job_id, user_id)
        if not job:
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
        logger.error(f"Error getting job status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user_id: str = Depends(get_user_id)
):
    """
    Generate a response based on a query and document context.
    
    This endpoint performs similarity search to find relevant documents,
    then generates a response based on the query and context.
    """
    logger.info(f"Chat request received from user {user_id}")
    
    try:
        # Perform similarity search
        similar_docs = embedder.similarity_search(
            query=request.query,
            user_id=user_id,
            top_k=request.top_k
        )
        
        if not similar_docs:
            return ChatResponse(
                response="I couldn't find any relevant information to answer your question.",
                sources=[],
                status="no_results"
            )
        
        # In a real implementation, you would use these docs with an LLM
        # For now, we'll return a placeholder response with the sources
        context = "\n".join([doc["content"] for doc in similar_docs])
        
        response = f"Based on the documents I've found, I can provide information related to your query. Here's what I found: {context[:100]}..."
        
        sources = [
            {
                "content": doc["content"][:200] + "...",
                "metadata": doc["metadata"],
                "similarity": doc["similarity"]
            } 
            for doc in similar_docs
        ]
        
        return ChatResponse(
            response=response,
            sources=sources
        )
    except HTTPException as e:
        logger.error(f"HTTP error in chat endpoint: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating response: {str(e)}")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check if the service is healthy."""
    return HealthResponse()

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    uvicorn.run("main:app", host=host, port=port, reload=debug)