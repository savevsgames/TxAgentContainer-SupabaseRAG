import os
import io
import fitz  # PyMuPDF
import docx
import torch
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
from transformers import AutoTokenizer, AutoModel
from dotenv import load_dotenv
import json

# Import from centralized auth service
from core.auth_service import auth_service
from core import (
    with_retry, 
    DocumentProcessingError, 
    EmbeddingError, 
    StorageError, 
    validate_file_type,
    request_logger
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("embedder")

# Supabase configuration
storage_bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "documents")

# BioBERT model configuration
model_name = os.getenv("MODEL_NAME", "dmis-lab/biobert-v1.1")
embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", "768"))
device = os.getenv("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
max_tokens = int(os.getenv("MAX_TOKENS", "512"))
chunk_size = int(os.getenv("CHUNK_SIZE", "512"))
chunk_overlap = int(os.getenv("CHUNK_OVERLAP", "50"))

class Embedder:
    """BioBERT embedder for medical text documents."""
    
    def __init__(self):
        """Initialize the embedder with the BioBERT model."""
        logger.info(f"Initializing BioBERT embedder using {device}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name).to(device)
        self.model.eval()
        
        logger.info("Embedder initialized successfully")

    async def create_embedding_job(self, job_id: str, file_path: str, user_id: str, jwt: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new embedding job record using centralized auth service.

        Args:
            job_id: Unique identifier for the job
            file_path: Path to the file in Supabase Storage
            user_id: User ID who initiated the job
            jwt: JWT token for authenticated operations

        Returns:
            Created job record
        """
        logger.info(f"🔍 CREATE_EMBEDDING_JOB: Starting for user {user_id}")
        logger.info(f"🔍 CREATE_EMBEDDING_JOB: JWT provided: {bool(jwt)}")

        client = auth_service.get_authenticated_client(jwt)

        try:
            result = await client.from_("embedding_jobs").insert({
                "id": job_id,
                "file_path": file_path,
                "status": "pending",
                "user_id": user_id
            }).execute()

            logger.info(f"✅ CREATE_EMBEDDING_JOB: Successfully created job {job_id}")
            return result.data[0] if result.data else None

        except Exception as e:
            logger.error(f"❌ CREATE_EMBEDDING_JOB: Error creating embedding job: {str(e)}")
            logger.error(f"❌ CREATE_EMBEDDING_JOB: Exception type: {type(e).__name__}")
            raise



    async def update_job_status(
        self,
        job_id: str,
        status: str,
        chunk_count: Optional[int] = None,
        document_ids: Optional[List[str]] = None,
        error: Optional[str] = None,
        jwt: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update the status of an embedding job using centralized auth service.
        
        Args:
            job_id: Job identifier
            status: New status (pending, processing, completed, failed)
            chunk_count: Optional number of chunks processed
            document_ids: Optional list of created document IDs
            error: Optional error message if job failed
            jwt: JWT token for authenticated operations
            
        Returns:
            Updated job record
        """
        logger.info(f"🔍 UPDATE_JOB_STATUS: Updating job {job_id} to {status}")
        logger.info(f"🔍 UPDATE_JOB_STATUS: JWT provided: {bool(jwt)}")
        
        # Use centralized auth service to get authenticated client
        client = auth_service.get_authenticated_client(jwt)
        
        try:
            update_data = {
                "status": status,
                "updated_at": "now()"
            }
            
            if chunk_count is not None:
                update_data["chunk_count"] = chunk_count
                
            if document_ids:
                update_data["metadata"] = json.dumps({"document_ids": document_ids})
                
            if error:
                update_data["error"] = error
                
            result = client.table("embedding_jobs").update(
                update_data
            ).eq("id", job_id).execute()
            
            logger.info(f"✅ UPDATE_JOB_STATUS: Successfully updated job {job_id}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"❌ UPDATE_JOB_STATUS: Error updating job status: {str(e)}")
            logger.error(f"❌ UPDATE_JOB_STATUS: Exception type: {type(e).__name__}")
            raise

    async def get_job_status(self, job_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the current status of an embedding job.
        
        Args:
            job_id: Job identifier
            user_id: User ID for RLS check
            
        Returns:
            Job record if found, None otherwise
        """
        # Use anon client for read operations (RLS will filter by user)
        client = auth_service.get_authenticated_client()
        
        try:
            result = client.table("embedding_jobs").select("*").eq("id", job_id).eq("user_id", user_id).execute()
            
            if result.data:
                job = result.data[0]
                # Extract document IDs from metadata if present
                if job.get("metadata"):
                    metadata = json.loads(job["metadata"])
                    job["document_ids"] = metadata.get("document_ids", [])
                return job
            return None
        except Exception as e:
            logger.error(f"Error getting job status: {str(e)}")
            raise

    @with_retry(retries=3, delay=1.0, backoff=2.0, exceptions=(Exception,))
    def _download_file(self, file_path: str, jwt: Optional[str] = None) -> bytes:
        """
        Download a file from Supabase Storage using centralized auth service.
        
        Args:
            file_path: Path to the file in Supabase Storage
            jwt: Optional JWT token for authenticated downloads
            
        Returns:
            File content as bytes
        """
        logger.info(f"Downloading file: {file_path}")
        
        # Use centralized auth service to get authenticated client
        client = auth_service.get_authenticated_client(jwt)
        
        try:
            response = client.storage.from_(storage_bucket).download(file_path)
            logger.info(f"Downloaded file: {file_path}")
            return response
        except Exception as e:
            logger.error(f"Error downloading file {file_path}: {str(e)}")
            raise

    @with_retry(retries=2, delay=1.0, backoff=2.0, exceptions=(DocumentProcessingError,))
    def _extract_text_from_pdf(self, content: bytes) -> str:
        """
        Extract text from PDF content.
        
        Args:
            content: PDF content as bytes
            
        Returns:
            Extracted text as string
        """
        try:
            with fitz.open(stream=content, filetype="pdf") as pdf:
                text = ""
                for page in pdf:
                    text += page.get_text()
                return text
        except Exception as e:
            raise DocumentProcessingError(f"Error extracting text from PDF: {str(e)}")

    @with_retry(retries=2, delay=1.0, backoff=2.0, exceptions=(DocumentProcessingError,))
    def _extract_text_from_docx(self, content: bytes) -> str:
        """
        Extract text from DOCX content.
        
        Args:
            content: DOCX content as bytes
            
        Returns:
            Extracted text as string
        """
        try:
            doc = docx.Document(io.BytesIO(content))
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text
        except Exception as e:
            raise DocumentProcessingError(f"Error extracting text from DOCX: {str(e)}")

    def _split_text(self, text: str) -> List[str]:
        """
        Split text into chunks for embedding.
        
        Args:
            text: Input text to split
            
        Returns:
            List of text chunks
        """
        logger.info(f"Splitting text into chunks of size {chunk_size} with overlap {chunk_overlap}")
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - chunk_overlap):
            chunk = " ".join(words[i:i + chunk_size])
            chunks.append(chunk)
            
        logger.info(f"Created {len(chunks)} chunks")
        return chunks

    @with_retry(retries=2, delay=1.0, backoff=2.0, exceptions=(EmbeddingError,))
    def _create_embedding(self, text: str) -> List[float]:
        """
        Create embedding for a text chunk using BioBERT.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        try:
            # Tokenize with proper truncation to max_tokens
            inputs = self.tokenizer(
                text, 
                return_tensors="pt",
                max_length=max_tokens,
                padding="max_length",
                truncation=True
            ).to(device)
            
            # Generate embeddings with no gradient computation
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Use CLS token embedding (first token) as sentence representation
                embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()[0]
                
                # Ensure we get exactly 768 dimensions
                if embeddings.shape[0] != embedding_dimension:
                    logger.warning(f"Embedding dimension mismatch: got {embeddings.shape[0]}, expected {embedding_dimension}")
                    # Truncate or pad to correct dimension
                    if embeddings.shape[0] > embedding_dimension:
                        embeddings = embeddings[:embedding_dimension]
                    else:
                        # Pad with zeros if too short
                        padded = np.zeros(embedding_dimension)
                        padded[:embeddings.shape[0]] = embeddings
                        embeddings = padded
                
                return embeddings.tolist()
                
        except Exception as e:
            raise EmbeddingError(f"Error creating embedding: {str(e)}")

    def process_document(self, file_path: str, metadata: Dict[str, Any], jwt: Optional[str] = None) -> List[Dict[str, Any]]:
        """Process a document by downloading, extracting text, chunking, and embedding."""
        logger.info(f"Processing document: {file_path}")
        
        # Validate file type
        if not validate_file_type(file_path):
            raise DocumentProcessingError(f"Unsupported file type: {file_path}")
        
        try:
            # Download file
            content = self._download_file(file_path, jwt)
            
            # Extract text based on file extension
            text = ""
            if file_path.endswith(".pdf"):
                text = self._extract_text_from_pdf(content)
            elif file_path.endswith(".docx"):
                text = self._extract_text_from_docx(content)
            elif file_path.endswith((".txt", ".md")):
                text = content.decode("utf-8")
            
            if not text.strip():
                raise DocumentProcessingError(f"No text extracted from document: {file_path}")
            
            # Split text into chunks
            chunks = self._split_text(text)
            
            # Create embeddings for each chunk
            document_chunks = []
            for i, chunk in enumerate(chunks):
                try:
                    embedding = self._create_embedding(chunk)
                    document_chunk = {
                        "content": chunk,
                        "embedding": embedding,
                        "metadata": {
                            **metadata,
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                            "source_file": file_path
                        }
                    }
                    document_chunks.append(document_chunk)
                except EmbeddingError as e:
                    logger.error(f"Error embedding chunk {i}: {str(e)}")
                    # Continue with next chunk
                    continue
            
            if not document_chunks:
                raise DocumentProcessingError("Failed to create any valid document chunks")
            
            logger.info(f"Created {len(document_chunks)} document chunks with embeddings")
            return document_chunks
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            raise

    def store_embeddings(self, document_chunks: List[Dict[str, Any]], user_id: str, jwt: Optional[str] = None) -> List[str]:
        """
        Store document chunks and embeddings in Supabase using centralized auth service.
        
        Args:
            document_chunks: List of document chunks with embeddings
            user_id: User ID for RLS
            jwt: Optional JWT token for authenticated operations
            
        Returns:
            List of inserted document IDs
        """
        logger.info(f"🔍 STORE_EMBEDDINGS: Storing {len(document_chunks)} embeddings for user {user_id}")
        logger.info(f"🔍 STORE_EMBEDDINGS: JWT provided: {bool(jwt)}")
        
        # Use centralized auth service to get authenticated client
        client = auth_service.get_authenticated_client(jwt)
        
        document_ids = []
        
        for i, chunk in enumerate(document_chunks):
            try:
                logger.info(f"🔍 STORE_EMBEDDINGS: Storing chunk {i+1}/{len(document_chunks)}")
                
                # Insert document with embedding
                result = client.table("documents").insert({
                    "content": chunk["content"],
                    "embedding": chunk["embedding"],
                    "metadata": chunk["metadata"],
                    "user_id": user_id
                }).execute()
                
                # Get the inserted document ID
                if result.data and len(result.data) > 0:
                    document_ids.append(result.data[0]["id"])
                    logger.info(f"✅ STORE_EMBEDDINGS: Stored chunk {i+1} with ID {result.data[0]['id']}")
                else:
                    logger.error(f"❌ STORE_EMBEDDINGS: No data returned for chunk {i+1}")
                    
            except Exception as e:
                logger.error(f"❌ STORE_EMBEDDINGS: Error storing chunk {i+1}: {str(e)}")
                logger.error(f"❌ STORE_EMBEDDINGS: Exception type: {type(e).__name__}")
                raise
        
        logger.info(f"✅ STORE_EMBEDDINGS: Stored {len(document_ids)} embeddings successfully")
        return document_ids

    def similarity_search(self, query: str, user_id: str, top_k: int = 5, jwt: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Perform similarity search against stored embeddings using centralized auth service.
        
        Args:
            query: Query text
            user_id: User ID for RLS (not needed with updated function)
            top_k: Number of results to return
            jwt: Optional JWT token for authenticated operations
            
        Returns:
            List of similar documents with metadata
        """
        logger.info(f"🔍 SIMILARITY_SEARCH: Starting similarity search")
        logger.info(f"🔍 SIMILARITY_SEARCH: Query: {query[:100]}...")
        logger.info(f"🔍 SIMILARITY_SEARCH: User ID: {user_id}")
        logger.info(f"🔍 SIMILARITY_SEARCH: Top K: {top_k}")
        logger.info(f"🔍 SIMILARITY_SEARCH: JWT provided: {bool(jwt)}")
        
        try:
            # STEP 1: Create embedding for the query
            logger.info("🔍 SIMILARITY_SEARCH: STEP 1 - Creating query embedding")
            try:
                query_embedding = self._create_embedding(query)
                logger.info(f"✅ SIMILARITY_SEARCH: Query embedding created successfully")
                logger.info(f"🔍 SIMILARITY_SEARCH: Embedding dimension: {len(query_embedding)}")
            except Exception as e:
                logger.error(f"❌ SIMILARITY_SEARCH: STEP 1 FAILED - Error creating query embedding: {str(e)}")
                raise EmbeddingError(f"Failed to create query embedding: {str(e)}")
            
            # STEP 2: Get Supabase client with JWT token using centralized auth service
            logger.info("🔍 SIMILARITY_SEARCH: STEP 2 - Getting authenticated Supabase client")
            try:
                client = auth_service.get_authenticated_client(jwt)
                logger.info(f"✅ SIMILARITY_SEARCH: Supabase client obtained")
            except Exception as e:
                logger.error(f"❌ SIMILARITY_SEARCH: STEP 2 FAILED - Error getting Supabase client: {str(e)}")
                raise StorageError(f"Failed to get Supabase client: {str(e)}")
            
            # STEP 3: Prepare RPC parameters for the standardized function
            logger.info("🔍 SIMILARITY_SEARCH: STEP 3 - Preparing RPC parameters")
            rpc_params = {
                "query_embedding": query_embedding,
                "match_threshold": 0.5,
                "match_count": top_k
                # Note: No query_user_id parameter - RLS handles user filtering automatically
            }
            logger.info(f"🔍 SIMILARITY_SEARCH: RPC function: match_documents")
            logger.info(f"🔍 SIMILARITY_SEARCH: RPC parameters: {list(rpc_params.keys())}")
            
            # STEP 4: Execute RPC call to the standardized match_documents function
            logger.info("🔍 SIMILARITY_SEARCH: STEP 4 - Executing RPC call to match_documents")
            try:
                logger.info("🔍 SIMILARITY_SEARCH: Calling client.rpc('match_documents', params)")
                result = client.rpc("match_documents", rpc_params).execute()
                logger.info(f"✅ SIMILARITY_SEARCH: RPC call completed successfully")
                
                # Check for errors in result
                if hasattr(result, 'error') and result.error:
                    logger.error(f"❌ SIMILARITY_SEARCH: Supabase RPC returned error: {result.error}")
                    raise StorageError(f"Supabase RPC error: {result.error}")
                
            except Exception as e:
                logger.error(f"❌ SIMILARITY_SEARCH: STEP 4 FAILED - RPC call error: {str(e)}")
                logger.error(f"❌ SIMILARITY_SEARCH: Exception type: {type(e).__name__}")
                
                # Check for specific error patterns
                if "'dict' object has no attribute 'headers'" in str(e):
                    logger.error(f"🚨 SIMILARITY_SEARCH: DETECTED 'headers' error - likely auth/client issue")
                
                raise StorageError(f"RPC call to match_documents failed: {str(e)}")
            
            # STEP 5: Process and return results
            logger.info("🔍 SIMILARITY_SEARCH: STEP 5 - Processing results")
            try:
                search_results = result.data if hasattr(result, 'data') else []
                logger.info(f"✅ SIMILARITY_SEARCH: Found {len(search_results)} matching documents")
                
                if search_results:
                    logger.info(f"🔍 SIMILARITY_SEARCH: Sample result structure: {list(search_results[0].keys())}")
                    for i, doc in enumerate(search_results[:3]):  # Log first 3 results
                        similarity = doc.get('similarity', 'unknown')
                        content_preview = doc.get('content', '')[:50] + '...' if doc.get('content') else 'No content'
                        logger.info(f"🔍 SIMILARITY_SEARCH: Result {i+1}: similarity={similarity}, content='{content_preview}'")
                else:
                    logger.info(f"ℹ️ SIMILARITY_SEARCH: No matching documents found")
                
                return search_results
                
            except Exception as e:
                logger.error(f"❌ SIMILARITY_SEARCH: STEP 5 FAILED - Error processing results: {str(e)}")
                raise StorageError(f"Failed to process search results: {str(e)}")
            
        except Exception as e:
            logger.error(f"❌ SIMILARITY_SEARCH: OVERALL FAILURE - {str(e)}")
            logger.error(f"❌ SIMILARITY_SEARCH: Final exception type: {type(e).__name__}")
            
            # Re-raise with more context
            if isinstance(e, (EmbeddingError, StorageError)):
                raise
            else:
                raise StorageError(f"Similarity search failed: {str(e)}")