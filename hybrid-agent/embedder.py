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

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
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

    def _extract_text_from_pdf(self, content: bytes) -> str:
        """
        Extract text from PDF content.
        
        Args:
            content: PDF content as bytes
            
        Returns:
            Extracted text as string
        """
        logger.info("Extracting text from PDF")
        text = ""
        
        try:
            with fitz.open(stream=content, filetype="pdf") as pdf:
                for page in pdf:
                    text += page.get_text()
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            return ""

    def _extract_text_from_docx(self, content: bytes) -> str:
        """
        Extract text from DOCX content.
        
        Args:
            content: DOCX content as bytes
            
        Returns:
            Extracted text as string
        """
        logger.info("Extracting text from DOCX")
        text = ""
        
        try:
            doc = docx.Document(io.BytesIO(content))
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text
        except Exception as e:
            logger.error(f"Error extracting text from DOCX: {str(e)}")
            return ""

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

    @torch.no_grad()
    def _create_embedding(self, text: str) -> List[float]:
        """
        Create embedding for a text chunk using BioBERT.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        # Tokenize and prepare input
        inputs = self.tokenizer(text, return_tensors="pt", 
                               max_length=max_tokens, 
                               padding="max_length", 
                               truncation=True).to(device)
        
        # Get model output
        outputs = self.model(**inputs)
        
        # Use CLS token embedding as the sentence embedding
        embeddings = outputs.last_hidden_state[:, 0, :].cpu().numpy()[0].tolist()
        
        return embeddings

    def process_document(self, file_path: str, metadata: Dict[str, Any], jwt: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Process a document by downloading, extracting text, chunking, and embedding.
        
        Args:
            file_path: Path to the file in Supabase Storage
            metadata: Metadata for the document
            jwt: Optional JWT token for authenticated operations
            
        Returns:
            List of document chunks with embeddings and metadata
        """
        logger.info(f"Processing document: {file_path}")
        
        # Download file
        content = self._download_file(file_path, jwt)
        
        # Extract text based on file extension
        text = ""
        if file_path.endswith(".pdf"):
            text = self._extract_text_from_pdf(content)
        elif file_path.endswith(".docx"):
            text = self._extract_text_from_docx(content)
        elif file_path.endswith(".txt") or file_path.endswith(".md"):
            text = content.decode("utf-8")
        else:
            logger.warning(f"Unsupported file type: {file_path}")
            return []
        
        if not text:
            logger.warning(f"No text extracted from document: {file_path}")
            return []
        
        # Split text into chunks
        chunks = self._split_text(text)
        
        # Create embeddings for each chunk
        document_chunks = []
        for i, chunk in enumerate(chunks):
            embedding = self._create_embedding(chunk)
            
            # Create document chunk with metadata
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
            
        logger.info(f"Created {len(document_chunks)} document chunks with embeddings")
        return document_chunks

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
            return []