import json
import logging
from pathlib import Path
from functools import lru_cache
from fastapi import APIRouter, Depends, HTTPException, status

from app.schemas import IngestBatchRequest, IngestResponse, DeleteVectorsResponse
from app.embedding_service import EmbeddingService
from app.qdrant_service import QdrantService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingest", tags=["Ingest"])

@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    return EmbeddingService()

@lru_cache(maxsize=1)
def get_qdrant_service() -> QdrantService:
    return QdrantService()

@router.post("", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
def ingest_chunks(
    payload: IngestBatchRequest,
    embedder: EmbeddingService = Depends(get_embedding_service),
    qdrant: QdrantService = Depends(get_qdrant_service)
) -> IngestResponse:
    """
    Ingest a batch of chunks: generates vector embeddings and upserts points into Qdrant.
    """
    raw_chunks = [chunk.model_dump() for chunk in payload.chunks]
    try:
        embedded_chunks = embedder.embed_chunks(raw_chunks)
        upserted_count = qdrant.upsert_chunks(embedded_chunks)
        total_in_db = qdrant.count()

        return IngestResponse(
            success=True,
            upserted_count=upserted_count,
            collection_name=qdrant.collection_name,
            total_points_in_db=total_in_db
        )
    except Exception as exc:
        logger.error(f"Error during chunk ingestion: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ingestion failed: {str(exc)}"
        )

@router.delete("/documents/{document_id}", response_model=DeleteVectorsResponse)
def delete_document_vectors(
    document_id: str,
    version_id: str | None = None,
    qdrant: QdrantService = Depends(get_qdrant_service)
) -> DeleteVectorsResponse:
    """Remove every vector belonging to a document, or just one version. Safe to call repeatedly."""
    try:
        deleted_count = qdrant.delete_by_document_id(document_id, version_id=version_id)
        return DeleteVectorsResponse(
            success=True,
            deleted_count=deleted_count,
            total_points_in_db=qdrant.count()
        )
    except Exception as exc:
        logger.error(f"Error deleting vectors for document {document_id}: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vector deletion failed: {str(exc)}"
        )

@router.post("/bootstrap-debug", response_model=IngestResponse, status_code=status.HTTP_200_OK)
def bootstrap_debug_data(
    qdrant: QdrantService = Depends(get_qdrant_service),
    embedder: EmbeddingService = Depends(get_embedding_service)
) -> IngestResponse:
    """
    Seed/bootstrap Qdrant collection using precomputed debug chunks if available.
    """
    embedded_file = Path("debug/06_embedded_chunks.json")
    enriched_file = Path("debug/05_enriched_chunks.json")

    try:
        if embedded_file.exists():
            chunks = json.loads(embedded_file.read_text(encoding="utf-8"))
            upserted = qdrant.upsert_chunks(chunks)
        elif enriched_file.exists():
            chunks = json.loads(enriched_file.read_text(encoding="utf-8"))
            embedded_chunks = embedder.embed_chunks(chunks)
            upserted = qdrant.upsert_chunks(embedded_chunks)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No preprocessed debug files found (05_enriched_chunks.json or 06_embedded_chunks.json)"
            )

        total_in_db = qdrant.count()
        return IngestResponse(
            success=True,
            upserted_count=upserted,
            collection_name=qdrant.collection_name,
            total_points_in_db=total_in_db
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error bootstrapping debug data: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bootstrap failed: {str(exc)}"
        )
