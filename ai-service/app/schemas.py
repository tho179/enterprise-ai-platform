from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ChunkMetadata(BaseModel):
    document_id: Optional[str] = None
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    section_path: List[str] = Field(default_factory=list)
    document_type: Optional[str] = None

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of chunks to retrieve")
    document_id: Optional[str] = Field(default=None, description="Optional document ID to filter results")
    min_score: float = Field(default=0.3, ge=0.0, le=1.0, description="Minimum cosine similarity threshold")

class SearchResultItem(BaseModel):
    chunk_id: Optional[str] = None
    score: float
    content: str
    metadata: ChunkMetadata

class SearchResponse(BaseModel):
    success: bool = True
    query: str
    total: int
    execution_time_ms: float
    data: List[SearchResultItem]

class IngestChunkItem(BaseModel):
    chunk_id: str
    content: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class IngestBatchRequest(BaseModel):
    chunks: List[IngestChunkItem] = Field(..., min_items=1, description="List of chunks to ingest")

class IngestResponse(BaseModel):
    success: bool = True
    upserted_count: int
    collection_name: str
    total_points_in_db: int

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
