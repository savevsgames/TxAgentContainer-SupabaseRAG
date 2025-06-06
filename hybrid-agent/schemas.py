from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import uuid

class DocumentMetadata(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    source: Optional[str] = None
    date: Optional[str] = None
    category: Optional[str] = None
    page: Optional[int] = None
    total_pages: Optional[int] = None
    chunk_index: Optional[int] = None
    total_chunks: Optional[int] = None
    source_file: Optional[str] = None
    custom: Optional[Dict[str, Any]] = Field(default_factory=dict)

class DocumentChunk(BaseModel):
    content: str
    embedding: List[float]
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    user_id: str
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))

class DocumentRequest(BaseModel):
    file_path: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class EmbedResponse(BaseModel):
    document_ids: List[str] = Field(default_factory=list)
    chunk_count: int = 0
    status: str = "success"
    message: str = "Document embedded successfully"

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    query: str
    history: List[ChatMessage] = Field(default_factory=list)
    top_k: int = 5
    temperature: float = 0.7
    stream: bool = False
    metadata_filter: Optional[Dict[str, Any]] = None

class Source(BaseModel):
    content: str
    metadata: DocumentMetadata
    similarity: float

class ChatResponse(BaseModel):
    response: str
    sources: List[Source] = Field(default_factory=list)
    status: str = "success"

class HealthResponse(BaseModel):
    status: str = "healthy"
    model: str
    device: str
    version: str = "1.0.0"