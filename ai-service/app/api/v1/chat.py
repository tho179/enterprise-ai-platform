import logging
from functools import lru_cache
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas import AskRequest, AskResponse
from app.rag_service import RAGService
from app.api.v1.search import get_retriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat & RAG"])

@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    """
    Cached singleton provider for RAGService reusing the cached VectorRetriever.
    """
    retriever = get_retriever()
    return RAGService(retriever=retriever)

@router.post("/ask", response_model=AskResponse, status_code=status.HTTP_200_OK)
def ask_document_question(
    payload: AskRequest,
    rag_service: RAGService = Depends(get_rag_service)
) -> AskResponse:
    """
    Submit a natural language question about enterprise documents.
    Retrieves the most relevant knowledge chunks and generates an answer with citations.
    """
    cleaned_query = payload.query.strip()
    if not cleaned_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question query cannot be empty"
        )

    try:
        response = rag_service.ask(
            query=cleaned_query,
            top_k=payload.top_k,
            document_id=payload.document_id,
            min_score=payload.min_score,
            history=payload.history
        )
        return response
    except Exception as exc:
        logger.error(f"Error executing RAG ask workflow: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate answer: {str(exc)}"
        )
