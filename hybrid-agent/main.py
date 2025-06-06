import os
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Header, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv

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

class ChatRequest(BaseModel):
    query: str
    history: List[Dict[str, str]] = []
    top_k: int = 5
    temperature: float = 0.7
    stream: bool = False

class EmbedResponse(BaseModel):
    document_ids: List[str]
    chunk_count: int
    status: str = "success"
    message: str = "Document embedded successfully"

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
async def process_document_task(file_path: str, metadata: Dict[str, Any], user_id: str, jwt: str):
    """Background task to process and embed a document."""
    logger.info(f"Processing document in background: {file_path} for user {user_id}")
    
    try:
        # Process document
        document_chunks = embedder.process_document(file_path, metadata, jwt)
        
        # Store embeddings
        document_ids = embedder.store_embeddings(document_chunks, user_id, jwt)
        
        logger.info(f"Background processing complete: {len(document_ids)} chunks embedded")
    except Exception as e:
        logger.error(f"Error in background processing: {str(e)}")

# API Endpoints
@app.post("/embed", response_model=EmbedResponse)
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
        
        # Schedule background task
        background_tasks.add_task(
            process_document_task,
            request.file_path,
            request.metadata,
            user_id,
            token
        )
        
        return EmbedResponse(
            document_ids=[],  # IDs will be generated during background processing
            chunk_count=0,    # Count will be determined during processing
            status="processing",
            message=f"Document {request.file_path} is being processed in the background"
        )
    except HTTPException as e:
        logger.error(f"HTTP error in embed endpoint: {e.detail}")
        raise
    except Exception as e:
        logger.error(f"Error in embed endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

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