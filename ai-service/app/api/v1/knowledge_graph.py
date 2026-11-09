"""
Knowledge Graph API Controller (KB1, KB2, KB Merge, and Update Pipeline)
Exposes REST endpoints for Neo4j GraphRAG operations.
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.config import settings
from app.knowledge_graph.pipeline import (
    KB,
    KB1,
    KB2,
    load_links,
    load_pdf,
    load_pdf_folder,
    merge,
)
from app.knowledge_graph.store import Neo4jStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge-graph", tags=["Knowledge Graph (Neo4j)"])


def get_store() -> Neo4jStore:
    """Helper to acquire Neo4jStore instance with credentials from environment."""
    return Neo4jStore(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "eakwp-neo4j"),
        database=os.getenv("NEO4J_DATABASE", "neo4j"),
    )


# ─── Pydantic Request Models ──────────────────────────────────────────────────

class LoadPdfPathRequest(BaseModel):
    path: str = Field(..., description="Server path to PDF file or directory")
    kb_id: str = Field(KB1, description="Target KB identifier (default KB1)")
    update: bool = Field(False, description="Enable hash-based versioned incremental update")


class LoadLinksRequest(BaseModel):
    urls: List[str] = Field(..., description="List of web URLs to parse and ingest")
    kb_id: str = Field(KB2, description="Target KB identifier (default KB2)")
    update: bool = Field(False, description="Enable hash-based versioned incremental update")


class MergeKBsRequest(BaseModel):
    sources: List[str] = Field([KB1, KB2], description="Source KB IDs to merge into unified KB")
    target: str = Field(KB, description="Target unified KB identifier (default KB)")


# ─── API Endpoints ────────────────────────────────────────────────────────────

@router.post("/init-schema", summary="Initialize Neo4j Constraints and Indexes")
def init_graph_schema():
    """Applies unique constraints and indexes on Document, Chunk, Entity, KnowledgeBase."""
    store = get_store()
    try:
        store.verify()
        store.init_schema()
        return {
            "success": True,
            "message": "Neo4j schema constraints and indexes successfully initialized"
        }
    except Exception as exc:
        logger.error(f"Failed to initialize Neo4j schema: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Neo4j connection or initialization failed: {exc}"
        )
    finally:
        store.close()


@router.post("/kb1/load-pdf", summary="Load a PDF into KB1 (via File Upload)")
async def load_pdf_file(
    file: UploadFile = File(...),
    update: bool = False,
    background_tasks: BackgroundTasks = None
):
    """
    KB1 Pipeline:
    Upload a PDF -> Adaptive Chunking -> Entity Extraction -> Neo4j Ingestion (KB1).
    """
    temp_dir = tempfile.mkdtemp()
    temp_path = os.path.join(temp_dir, file.filename)
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        store = get_store()
        try:
            store.verify()
            res = load_pdf(store, temp_path, kb_id=KB1, title=file.filename, update=update)
            return {
                "success": True,
                "data": res
            }
        finally:
            store.close()
    except Exception as exc:
        logger.error(f"Error ingesting PDF {file.filename}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ingest PDF into KB1: {exc}"
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/kb1/load-path", summary="Load PDF(s) from Server Path into KB1")
def load_pdf_path(payload: LoadPdfPathRequest):
    """
    KB1 Pipeline:
    Scans a local path or directory of PDFs and ingests them into KB1 in Neo4j.
    """
    target_path = Path(payload.path)
    if not target_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Path not found: {payload.path}"
        )

    store = get_store()
    try:
        store.verify()
        if target_path.is_dir():
            res = load_pdf_folder(store, str(target_path), kb_id=payload.kb_id, update=payload.update)
        else:
            res = load_pdf(store, str(target_path), kb_id=payload.kb_id, update=payload.update)
        return {
            "success": True,
            "data": res
        }
    except Exception as exc:
        logger.error(f"Failed to load PDFs from path {payload.path}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        )
    finally:
        store.close()


@router.post("/kb2/load-links", summary="Ingest Web URLs into KB2")
def ingest_web_links(payload: LoadLinksRequest):
    """
    KB2 Pipeline:
    Fetches web URLs -> Extracts text/HTML -> Chunks -> Entity Extraction -> Neo4j Ingestion (KB2).
    """
    store = get_store()
    try:
        store.verify()
        res = load_links(store, payload.urls, kb_id=payload.kb_id, update=payload.update)
        return {
            "success": True,
            "data": res
        }
    except Exception as exc:
        logger.error(f"Failed to load web links: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        )
    finally:
        store.close()


@router.post("/kb/merge", summary="Merge KB1 and KB2 into Unified KB")
def merge_knowledge_bases(payload: MergeKBsRequest):
    """
    KB Merge Pipeline:
    Merges documents and chunks from KB1 and KB2 into a unified 'KB'.
    Deduplication is guaranteed via content-addressed hashing (SHA-1).
    """
    store = get_store()
    try:
        store.verify()
        res = merge(store, sources=tuple(payload.sources), target=payload.target)
        return {
            "success": True,
            "data": res
        }
    except Exception as exc:
        logger.error(f"Failed to merge knowledge bases: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        )
    finally:
        store.close()


@router.get("/stats", summary="Get Statistics of Knowledge Bases")
def get_kb_stats(kb_id: str = KB):
    """Returns total documents, chunks, and entities in the specified KB."""
    store = get_store()
    try:
        store.verify()
        stats = store.stats(kb_id=kb_id)
        return {
            "success": True,
            "kb_id": kb_id,
            "data": stats
        }
    except Exception as exc:
        logger.error(f"Failed to retrieve KB stats: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        )
    finally:
        store.close()


@router.get("/sample", summary="Sample Nodes from KB for Graph Visualization")
def get_kb_sample(kb_id: str = KB, chunk_limit: int = 5):
    """Returns sample documents, chunks, and entities for UI visualization."""
    store = get_store()
    try:
        store.verify()
        data = store.sample(kb_id=kb_id, chunk_limit=chunk_limit)
        return {
            "success": True,
            "data": data
        }
    except Exception as exc:
        logger.error(f"Failed to sample KB data: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc)
        )
    finally:
        store.close()

