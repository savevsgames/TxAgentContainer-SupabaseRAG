import os
import io
import fitz  # PyMuPDF
import docx
import torch
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
from transformers import AutoTokenizer, AutoModel
from tenacity import retry, stop_after_attempt, wait_exponential
from supabase import create_client, Client
from dotenv import load_dotenv
import json
from utils import with_retry, DocumentProcessingError, EmbeddingError, StorageError, validate_file_type

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("embedder")

# Supabase configuration
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase_service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
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
        
        # Initialize Supabase clients - one with anon key, one with service role
        self.supabase = create_client(supabase_url, supabase_key)
        self.supabase_admin = create_client(supabase_url, supabase_service_key) if supabase_service_key else None
        
        logger.info("Embedder initialized successfully")

    def _get_supabase_client(self, jwt: Optional[str] = None) -> Client:
        """
        Get the appropriate Supabase client based on JWT presence.
        
        Args:
            jwt: Optional JWT token for authenticated operations
            
        Returns:
            Supabase client instance
        """
        if jwt:
            # Create a new client with the provided JWT
            return create_client(supabase_url, supabase_key, {
                "Authorization": f"Bearer {jwt}"
            })
        else:
            # Use default client with anon key
            return self.supabase

    async def create_embedding_job(self, job_id: str, file_path: str, user_id: str) -> Dict[str, Any]:
        """
        Create a new embedding job record.
        
        Args:
            job_id: Unique identifier for the job
            file_path: Path to the file in Supabase Storage
            user_id: User ID who initiated the job
            
        Returns:
            Created job record
        """
        client = self._get_supabase_client()
        
        try:
            result = client.table("embedding_jobs").insert({
                "id": job_id,
                "file_path": file_path,
                "status": "pending",
                "user_id": user_id
            }).execute()
            
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating embedding job: {str(e)}")
            raise

    async def update_job_status(
        self,
        job_id: str,
        status: str,
        chunk_count: Optional[int] = None,
        document_ids: Optional[List[str]] = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update the status of an embedding job.
        
        Args:
            job_id: Job identifier
            status: New status (pending, processing, completed, failed)
            chunk_count: Optional number of chunks processed
            document_ids: Optional list of created document IDs
            error: Optional error message if job failed
            
        Returns:
            Updated job record
        """
        client = self._get_supabase_client()
        
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
            
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error updating job status: {str(e)}")
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
        client = self._get_supabase_client()
        
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
        Download a file from Supabase Storage.
        
        Args:
            file_path: Path to the file in Supabase Storage
            jwt: Optional JWT token for authenticated downloads
            
        Returns:
            File content as bytes
        """
        logger.info(f"Downloading file: {file_path}")
        
        client = self._get_supabase_client(jwt)
        
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
            inputs = self.tokenizer(text, return_tensors="pt",
                                  max_length=max_tokens,
                                  padding="max_length",
                                  truncation=True).to(device)
            outputs = self.model(**inputs)
            embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()[0].tolist()
            return embeddings
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
        Store document chunks and embeddings in Supabase.
        
        Args:
            document_chunks: List of document chunks with embeddings
            user_id: User ID for RLS
            jwt: Optional JWT token for authenticated operations
            
        Returns:
            List of inserted document IDs
        """
        logger.info(f"Storing {len(document_chunks)} embeddings for user {user_id}")
        
        client = self._get_supabase_client(jwt)
        document_ids = []
        
        for chunk in document_chunks:
            try:
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
                    
            except Exception as e:
                logger.error(f"Error storing embedding: {str(e)}")
                raise
        
        logger.info(f"Stored {len(document_ids)} embeddings successfully")
        return document_ids

    def similarity_search(self, query: str, user_id: str, top_k: int = 5, jwt: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Perform similarity search against stored embeddings.
        
        Args:
            query: Query text
            user_id: User ID for RLS
            top_k: Number of results to return
            jwt: Optional JWT token for authenticated operations
            
        Returns:
            List of similar documents with metadata
        """
        logger.info(f"Performing similarity search for query: {query}")
        
        # Create embedding for the query
        query_embedding = self._create_embedding(query)
        
        client = self._get_supabase_client(jwt)
        
        try:
            # Perform similarity search in Supabase pgvector
            result = client.rpc(
                "match_documents",
                {
                    "query_embedding": query_embedding,
                    "match_threshold": 0.5,
                    "match_count": top_k,
                    "query_user_id": user_id
                }
            ).execute()
            
            logger.info(f"Found {len(result.data)} matching documents")
            return result.data
        except Exception as e:
            logger.error(f"Error performing similarity search: {str(e)}")
            raise