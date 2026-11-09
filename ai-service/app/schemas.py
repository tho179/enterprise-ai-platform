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
    user_roles: Optional[List[str]] = Field(default=None, description="Set by the backend gateway; None means no role filter")

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
    chunk_index: Optional[int] = None
    content: str
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class IngestBatchRequest(BaseModel):
    chunks: List[IngestChunkItem] = Field(..., min_length=1, description="List of chunks to ingest")

class IngestResponse(BaseModel):
    success: bool = True
    upserted_count: int
    collection_name: str
    total_points_in_db: int
    graph_synced_count: int = 0

class DeleteVectorsResponse(BaseModel):
    success: bool = True
    deleted_count: int
    total_points_in_db: int
    graph_deleted_count: int = 0

class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the speaker: 'user' or 'assistant'")
    content: str = Field(..., description="Message text content")

class CitationItem(BaseModel):
    index: int
    chunk_id: str
    score: float
    document_id: Optional[str] = None
    section_path: List[str] = Field(default_factory=list)
    pages: str
    snippet: str

class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language question")
    top_k: int = Field(default=3, ge=1, le=10, description="Number of context chunks to retrieve")
    document_id: Optional[str] = Field(default=None, description="Filter question context to a specific document ID")
    min_score: float = Field(default=0.35, ge=0.0, le=1.0, description="Minimum similarity threshold")
    history: Optional[List[ChatMessage]] = Field(default_factory=list, description="Previous conversation messages for multi-turn chat")
    user_roles: Optional[List[str]] = Field(default=None, description="Set by the backend gateway; None means no role filter")

class AskResponse(BaseModel):
    success: bool = True
    query: str
    answer: str
    citations: List[CitationItem]
    execution_time_ms: float
    model_used: str
    graph_candidates: int = 0
    verified: Optional[bool] = None
    timings_ms: Dict[str, float] = Field(default_factory=dict)
    # Chỉ dùng cho benchmark: top-k trước bước lọc câu trả lời.
    retrieved_chunk_ids: List[str] = Field(default_factory=list)
    retrieved_contents: List[str] = Field(default_factory=list)

class ExtractedWord(BaseModel):
    """Một từ với tọa độ khung hình theo tỷ lệ 0..1 (x, y là góc trên-trái)."""
    text: str
    x: float
    y: float
    w: float
    h: float

class ExtractedPage(BaseModel):
    page: int
    text: str
    source: str
    words: List[ExtractedWord] = Field(default_factory=list)

class ExtractedChunk(BaseModel):
    index: int
    pageStart: int
    pageEnd: int
    headingLevel: int = 0
    sectionPath: List[str] = Field(default_factory=list)
    content: str

class ExtractResponse(BaseModel):
    success: bool = True
    pageCount: int
    nativePages: int
    ocrPages: int
    pages: List[ExtractedPage]
    chunks: List[ExtractedChunk] = Field(default_factory=list)

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail
