"""Bridge between the request path and Neo4j.

The graph is optional: every helper degrades to a no-op when Neo4j is off or
unreachable, so uploads and vector-only chat keep working.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any, Dict, Iterable, List, Optional

from app.config import settings
from app.embedding_service import fold_text
from app.knowledge_graph.enrich import enrich_entities
from app.knowledge_graph.extract import build_record_from_ingest_chunks, extract_entities
from app.knowledge_graph.pipeline import KB
from app.knowledge_graph.store import Neo4jStore

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_store: Optional[Neo4jStore] = None
_disabled_until = 0.0


def get_store() -> Neo4jStore:
    """Return one shared driver, creating the schema on first use."""
    global _store
    with _lock:
        if _store is None:
            store = Neo4jStore(
                uri=settings.NEO4J_URI,
                user=settings.NEO4J_USER,
                password=settings.NEO4J_PASSWORD,
                database=settings.NEO4J_DATABASE,
            )
            try:
                store.verify()
                store.init_schema()
            except Exception:
                store.close()
                raise
            _store = store
        return _store


def reset_store() -> None:
    """Close the shared driver (tests/reloads)."""
    global _store
    with _lock:
        if _store is not None:
            _store.close()
            _store = None


def _mark_unavailable(exc: Exception) -> None:
    global _disabled_until
    _disabled_until = time.time() + 30.0
    logger.warning("Neo4j unavailable; graph features paused for 30s: %s", exc)


def _graph_enabled() -> bool:
    return settings.GRAPH_ENABLED and time.time() >= _disabled_until


def sync_ingest_chunks(
    chunks: Iterable[Dict[str, Any]],
    store: Optional[Neo4jStore] = None,
    force: bool = False,
) -> int:
    """Upsert backend chunks into Neo4j using the same chunk_id as Qdrant."""
    chunks = list(chunks)
    if not chunks:
        return 0
    if store is None and not force and not _graph_enabled():
        return 0

    records = build_record_from_ingest_chunks(chunks)
    if not records:
        return 0

    owns_store = store is None
    synced = 0
    try:
        store = store or get_store()
        for record in records:
            try:
                store.upsert_record(KB, "EAKWP Knowledge Base", record)
                synced += len(record["chunks"])
            except Exception as exc:  # one bad document must not drop the batch
                logger.warning(
                    "Graph sync failed for document %s: %s",
                    record["doc"].get("doc_id"),
                    exc,
                )
    except Exception as exc:
        if owns_store:
            _mark_unavailable(exc)
        else:
            logger.warning("Graph sync skipped: %s", exc)
    return synced


def enrich_new_entities(embedder: Any, store: Optional[Neo4jStore] = None) -> int:
    """Best effort: a missing description must never fail an upload."""
    if store is None and not _graph_enabled():
        return 0
    try:
        return enrich_entities(store or get_store(), embedder)
    except Exception as exc:
        logger.warning("Entity enrichment skipped: %s", exc)
        return 0


def delete_graph_document(
    document_id: str,
    version_id: Optional[str] = None,
    store: Optional[Neo4jStore] = None,
) -> int:
    """Remove graph chunks for one version, or the whole document."""
    if store is None and not _graph_enabled():
        return 0
    owns_store = store is None
    try:
        store = store or get_store()
        return store.delete_document(document_id, version_id=version_id)
    except Exception as exc:
        if owns_store:
            _mark_unavailable(exc)
        else:
            logger.warning("Graph delete skipped for %s: %s", document_id, exc)
        return 0


def graph_hit_from_row(row: Dict[str, Any], question: str = "") -> Dict[str, Any]:
    """Map a Cypher row to the same shape as a Qdrant hit."""
    content = str(row.get("content") or "")
    matched = int(row.get("matched") or 1)
    related = int(row.get("related") or 0)
    folded_content = fold_text(content)
    articles = re.findall(r"\bdieu\s+(\d{1,3})\b", fold_text(question))
    article_match = any(
        re.search(rf"\bdieu\s+{re.escape(article)}\b", folded_content)
        for article in articles
    )
    return {
        "chunk_id": row.get("chunk_id"),
        "content": content,
        "score": round(min(0.8, 0.55 + 0.05 * matched + (0.03 if related == 0 else 0.01)), 4),
        "graph_via": row.get("via", "entity"),
        "metadata": {
            "document_id": row.get("document_id"),
            "title": row.get("title"),
            "document_type": row.get("document_type"),
            "source_type": row.get("source_type"),
            "page_start": row.get("page_start"),
            "page_end": row.get("page_end"),
            "section_path": [
                str(item).strip()
                for item in (row.get("section_path") or [])
                if str(item).strip()
            ],
        },
        "from_graph": True,
        "article_match": article_match,
        "graph_related": related,
    }


def graph_search(
    question: str,
    limit: Optional[int] = None,
    document_id: Optional[str] = None,
    store: Optional[Neo4jStore] = None,
    enabled: Optional[bool] = None,
    source_type: Optional[str] = None,
    query_vector: Optional[List[float]] = None,
    seed_chunk_ids: Optional[List[str]] = None,
    allowed_roles: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Question entities -> chunks, then 1-2 hops out from the seed chunks."""
    if enabled is None:
        enabled = True if store is not None else _graph_enabled()
    if not enabled or not (question or "").strip():
        return []

    limit = limit or settings.GRAPH_SEARCH_LIMIT
    filters = {
        "source_type": source_type,
        "document_id": document_id,
        "allowed_roles": allowed_roles,
    }
    names = {entity["name"] for entity in extract_entities(question)}
    owns_store = store is None
    rows: List[Dict[str, Any]] = []
    try:
        store = store or get_store()
        lookup = getattr(store, "entity_names", None)
        if lookup is not None:
            folded_question = fold_text(question)
            for name in lookup(KB):
                folded_name = fold_text(name)
                if len(folded_name) < 3:
                    continue
                if re.search(
                    rf"(?<!\w){re.escape(folded_name)}(?!\w)",
                    folded_question,
                ):
                    names.add(name)
        similar = getattr(store, "similar_entities", None)
        if similar is not None and query_vector is not None:
            names.update(similar(query_vector, settings.GRAPH_ENTITY_MIN_SCORE))
        if names:
            rows.extend(
                store.graph_candidates(
                    names=sorted(names),
                    kb_ids=(KB,),
                    limit=limit,
                    **filters,
                )
            )
        expand = getattr(store, "expand_from_chunks", None)
        if expand is not None and seed_chunk_ids:
            rows.extend(
                expand(
                    seed_chunk_ids,
                    limit=limit,
                    max_entity_df=settings.GRAPH_MAX_ENTITY_DF,
                    **filters,
                )
            )
    except Exception as exc:
        if owns_store:
            _mark_unavailable(exc)
        else:
            logger.warning("Graph search skipped: %s", exc)
        return []

    hits: List[Dict[str, Any]] = []
    seen = set()
    for row in rows:
        chunk_id = row.get("chunk_id")
        if not chunk_id or chunk_id in seen:
            continue
        seen.add(chunk_id)
        hits.append(graph_hit_from_row(row, question))
    return hits
