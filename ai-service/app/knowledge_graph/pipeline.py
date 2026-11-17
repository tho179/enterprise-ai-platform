"""KB ingestion, merge, update and graph-retrieval helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from . import consistency, resolve
from .extract import build_link_record, build_pdf_record, extract_entities, source_uri_for

KB1 = "KB1"  # tài liệu PDF nghiệp vụ
KB2 = "KB2"  # nguồn công khai từ link
KB = "KB"    # kho hợp nhất dùng cho RAG


def plan_update(current: Optional[Dict[str, Any]], content_hash: str) -> str:
    """Decide insert / skip / new_version from the current document hash."""
    if not current:
        return "insert"
    if current.get("content_hash") == content_hash:
        return "skip"
    return "new_version"


def apply_record(store, record: Dict[str, Any], kb_id: str, update: bool = True) -> Dict[str, Any]:
    """Insert, skip or version one built record. Shared by PDF and link loading.

    insert       source never seen
    skip         same source, same content hash: nothing is written
    new_version  same source, new hash: the old Document stays in the graph
                 with is_current=false and the new one points to it
    """
    doc = record["doc"]
    current = store.find_current(doc["source_uri"]) if update else None
    action = plan_update(current, doc["content_hash"]) if update else "insert"
    if action == "skip":
        return {"action": "skip", "doc_id": current["doc_id"], "chunks": 0}

    old_id = None
    if action == "new_version":
        old_id = store.supersede(doc["source_uri"])
        doc["version"] = int(current.get("version", 1)) + 1

    store.upsert_record(kb_id, f"Kho {kb_id}", record)
    if old_id:
        store.link_version(old_id, doc["doc_id"])
    return {"action": action, "doc_id": doc["doc_id"], "chunks": len(record["chunks"]), "previous": old_id}


def load_pdf(
    store,
    path,
    kb_id: str = KB1,
    title: Optional[str] = None,
    update: bool = False,
) -> Dict[str, Any]:
    return apply_record(store, build_pdf_record(path, title=title), kb_id, update=update)


def load_links(
    store,
    urls: Iterable[str],
    kb_id: str = KB2,
    update: bool = False,
) -> Dict[str, Any]:
    loaded, failed = [], []
    for url in urls:
        try:
            result = apply_record(store, build_link_record(url), kb_id, update=update)
            loaded.append({"url": url, **result})
        except Exception as exc:
            failed.append({"url": url, "error": str(exc)})
    return {"loaded": loaded, "failed": failed}


def summarize(results: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    counts = {"inserted": 0, "skipped": 0, "new_version": 0, "failed": 0}
    for item in results:
        if item.get("error"):
            counts["failed"] += 1
        elif item.get("action") == "skip":
            counts["skipped"] += 1
        elif item.get("action") == "new_version":
            counts["new_version"] += 1
        else:
            counts["inserted"] += 1
    return counts


def log_run(store, kb_id: str, source: str, started_at: str, results: List[Dict[str, Any]], retired: int = 0) -> Dict[str, Any]:
    """Write one IngestRun node: the audit trail of KB updates."""
    counts = summarize(results)
    run_id = "run-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    store.log_run(
        run_id=run_id,
        kb_id=kb_id,
        source=source,
        started_at=started_at,
        retired=retired,
        **counts,
    )
    return {"run_id": run_id, **counts, "retired": retired}


def merge(store, sources: Sequence[str] = (KB1, KB2), target: str = KB) -> Dict[str, Any]:
    """Link all documents from KB1/KB2 into KB; content IDs dedupe automatically."""
    documents = store.merge_kbs(sources=sources, target=target, target_name="EAKWP Knowledge Base")
    return {"target": target, "sources": list(sources), "documents": documents, "stats": store.stats(target)}


def maintain(store) -> Dict[str, Any]:
    """Settle the problems created by merging sources. Safe to re-run.

    Order matters: duplicates and versions decide which documents are current,
    and claims are resolved on top of that.
    """
    docs = store.document_texts()
    duplicates = consistency.find_duplicates(docs)
    store.write_duplicates(duplicates)

    series = consistency.find_series(docs)
    store.write_series(series)

    entities = store.resolution_candidates(resolve.RESOLVABLE_TYPES)
    pairs = resolve.resolve_pairs(entities, manual=store.manual_decisions())
    store.write_entity_resolution(pairs)

    weights = store.recompute_relation_weights()

    keywords = [spec["phrase"] for spec in consistency.SINGLE_VALUED.values()]
    keywords += ["điều lệ", "dieu le", "mệnh giá", "menh gia"]
    chunks = [
        chunk for chunk in store.claim_source_chunks(keywords)
        if not chunk.get("duplicate_of")
    ]
    claims = [claim for chunk in chunks for claim in consistency.extract_claims(chunk)]
    claims, conflicts = consistency.resolve_conflicts(claims)
    written = store.write_claims(claims, conflicts)

    return {
        "duplicates": duplicates,
        "series": series,
        "entity_pairs": pairs,
        "relation_weights": weights,
        "claims": claims,
        "conflicts": conflicts,
        "written": written,
    }


def rrf_fuse(
    vector_hits: List[Dict[str, Any]],
    graph_hits: List[Dict[str, Any]],
    k: int = 60,
    graph_weight: float = 0.2,
) -> List[Dict[str, Any]]:
    """Reciprocal Rank Fusion of dense/lexical hits and graph hits."""
    merged: Dict[str, Dict[str, Any]] = {}
    scores: Dict[str, float] = {}

    def add(hits: List[Dict[str, Any]], weight: float) -> None:
        for rank, hit in enumerate(hits, start=1):
            cid = hit.get("chunk_id")
            if not cid:
                continue
            target = merged.setdefault(
                cid,
                {**hit, "metadata": dict(hit.get("metadata") or {})},
            )
            for key, value in hit.items():
                if value is None:
                    continue
                if key == "metadata" and isinstance(value, dict):
                    metadata = target.setdefault("metadata", {})
                    for meta_key, meta_value in value.items():
                        if metadata.get(meta_key) in (None, "", []):
                            metadata[meta_key] = meta_value
                elif isinstance(value, bool) and key in ("from_graph", "article_match"):
                    target[key] = bool(target.get(key)) or value
                elif target.get(key) in (None, "", []):
                    # Keep the vector score/rank when both sources agree.
                    target[key] = value
            scores[cid] = scores.get(cid, 0.0) + weight / (k + rank)

    add(vector_hits, 1.0)
    add(graph_hits, graph_weight)
    for cid, score in scores.items():
        merged[cid]["rrf_score"] = round(score, 6)
    return sorted(merged.values(), key=lambda item: item["rrf_score"], reverse=True)


def graph_context(store, question: str, kb_ids: Sequence[str] = (KB,), limit: int = 8) -> List[Dict[str, Any]]:
    """Entity -> chunk expansion; returns [] when the question has no known entity."""
    names = [entity["name"] for entity in extract_entities(question)]
    if not names:
        return []
    return store.graph_candidates(names=names, kb_ids=kb_ids, limit=limit)


def load_pdf_folder(
    store,
    folder,
    kb_id: str = KB1,
    update: bool = False,
    prune: bool = False,
) -> Dict[str, Any]:
    """Load every PDF under folder. With prune, documents whose file has
    disappeared are retired (is_current=false), never deleted."""
    started_at = datetime.now(timezone.utc).isoformat()
    paths = sorted(Path(folder).rglob("*.pdf"))
    results = []
    for path in paths:
        try:
            results.append({"path": str(path), **load_pdf(store, path, kb_id=kb_id, update=update)})
        except Exception as exc:
            results.append({"path": str(path), "error": str(exc)})
    retired: List[str] = []
    if prune:
        retired = store.retire_missing(
            kb_id=kb_id,
            source_type="pdf",
            prefix=source_uri_for(folder).rstrip("/") + "/",
            present=[source_uri_for(path) for path in paths],
        )
    run = log_run(store, kb_id, source_uri_for(folder), started_at, results, retired=len(retired))
    return {"loaded": results, "retired": retired, "run": run, "stats": store.stats(kb_id)}
