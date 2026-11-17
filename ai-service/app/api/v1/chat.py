import logging
from functools import lru_cache
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, status

from app.agent import RuleBasedAgent
from app.agent.rules import describe
from app.api.v1.search import get_retriever
from app.config import settings
from app.rag_service import RAGService
from app.schemas import AskRequest, AskResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat & RAG"])


@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    """
    Cached singleton provider for RAGService reusing the cached VectorRetriever.
    """
    retriever = get_retriever()
    return RAGService(
        retriever=retriever,
        graph_source_type=settings.CHAT_GRAPH_SOURCE_TYPE or None,
    )


@lru_cache(maxsize=1)
def get_agent() -> RuleBasedAgent:
    rag = get_rag_service()
    return RuleBasedAgent(rag=rag, source_type=rag.graph_source_type)


@router.post("/ask", response_model=AskResponse, status_code=status.HTTP_200_OK)
def ask_document_question(
    payload: AskRequest,
    rag_service: RAGService = Depends(get_rag_service),
) -> AskResponse:
    """
    Submit a natural language question about enterprise documents.
    The rule-based agent chooses the strategy (KB attribute lookup, vector or
    hybrid retrieval, retry, refusal) and records it in agent_trace.
    """
    cleaned_query = payload.query.strip()
    if not cleaned_query:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Question query cannot be empty"
        )

    answerer = get_agent() if settings.AGENT_ENABLED else rag_service
    try:
        return answerer.ask(
            query=cleaned_query,
            top_k=payload.top_k,
            document_id=payload.document_id,
            min_score=payload.min_score,
            history=payload.history,
            allowed_roles=payload.user_roles,
        )
    except Exception as exc:
        logger.error(f"Error executing RAG ask workflow: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate answer: {str(exc)}"
        )


@router.get("/agent/rules", summary="Rule table of the question-answering agent")
def agent_rules() -> List[Dict[str, Any]]:
    return describe()
