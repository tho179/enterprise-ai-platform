import time
import logging
from functools import lru_cache
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas import SearchRequest, SearchResponse, SearchResultItem
from app.retriever import VectorRetriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["Search"])

@lru_cache(maxsize=1)
def get_retriever() -> VectorRetriever:
    """
    Cached singleton provider for VectorRetriever to avoid reloading
    embedding model into memory on each request.
    """
    return VectorRetriever()

@router.post("", response_model=SearchResponse, status_code=status.HTTP_200_OK)
def search_documents(
    payload: SearchRequest,
    retriever: VectorRetriever = Depends(get_retriever)
) -> SearchResponse:
    """
    Perform semantic vector search against enterprise documents in Qdrant.
    Returns Top-K relevant chunks with similarity score and hierarchical metadata.
    """
    cleaned_query = payload.query.strip()
    if not cleaned_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty"
        )

    start_time = time.time()
    try:
        raw_results = retriever.search(
            query=cleaned_query,
            top_k=payload.top_k,
            document_id=payload.document_id,
            min_score=payload.min_score
        )
    except Exception as exc:
        logger.error(f"Error executing vector retrieval: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector search failed: {str(exc)}"
        )

    elapsed_ms = round((time.time() - start_time) * 1000, 2)

    items = [SearchResultItem(**item) for item in raw_results]

    return SearchResponse(
        success=True,
        query=cleaned_query,
        total=len(items),
        execution_time_ms=elapsed_ms,
        data=items
    )

@router.get("/stats")
def get_search_stats(
    retriever: VectorRetriever = Depends(get_retriever)
):
    """
    Get current collection statistics from Qdrant.
    """
    try:
        total_vectors = retriever.qdrant.count()
        return {
            "success": True,
            "collection_name": retriever.qdrant.collection_name,
            "total_points": total_vectors,
            "vector_dimension": retriever.embedding.vector_dim,
            "embedding_model": retriever.embedding.model_name
        }
    except Exception as exc:
        logger.error(f"Error fetching collection stats: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch collection stats: {str(exc)}"
        )
