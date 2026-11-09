"""KB ingestion, merge, update and graph-retrieval helpers."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .extract import build_link_record, build_pdf_record, extract_entities

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


def load_pdf(
    store,
    path,
    kb_id: str = KB1,
    title: Optional[str] = None,
    update: bool = False,
) -> Dict[str, Any]:
    record = build_pdf_record(path, title=title)
    doc = record["doc"]
    current = store.find_current(doc["source_uri"]) if update else None
    action = plan_update(current, doc["content_hash"]) if update else "insert"
    if action == "skip":
        return {"action": "skip", "doc_id": current["doc_id"], "chunks": 0}

    old_id = None
    if action == "new_version":
        old_id = store.supersede(doc["source_uri"])
        doc["version"] = int(current.get("version", 1)) + 1

    result = store.upsert_record(kb_id, f"Kho {kb_id}", record)
    if old_id:
        store.link_version(old_id, doc["doc_id"])
    return {"action": action, "doc_id": doc["doc_id"], "chunks": len(record["chunks"])}


def load_links(
    store,
    urls: Iterable[str],
    kb_id: str = KB2,
    update: bool = False,
) -> Dict[str, Any]:
    loaded, failed = [], []
    for url in urls:
        try:
            record = build_link_record(url)
            doc = record["doc"]
            current = store.find_current(doc["source_uri"]) if update else None
            action = plan_update(current, doc["content_hash"]) if update else "insert"
            if action == "skip":
                loaded.append({"url": url, "action": "skip", "doc_id": current["doc_id"]})
                continue
            old_id = None
            if action == "new_version":
                old_id = store.supersede(doc["source_uri"])
                doc["version"] = int(current.get("version", 1)) + 1
            store.upsert_record(kb_id, f"Kho {kb_id}", record)
            if old_id:
                store.link_version(old_id, doc["doc_id"])
            loaded.append({"url": url, "action": action, "doc_id": doc["doc_id"]})
        except Exception as exc:
            failed.append({"url": url, "error": str(exc)})
    return {"loaded": loaded, "failed": failed}


def merge(store, sources: Sequence[str] = (KB1, KB2), target: str = KB) -> Dict[str, Any]:
    """Link all documents from KB1/KB2 into KB; content IDs dedupe automatically."""
    documents = store.merge_kbs(sources=sources, target=target, target_name="EAKWP Knowledge Base")
    return {"target": target, "sources": list(sources), "documents": documents, "stats": store.stats(target)}


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


def load_pdf_folder(store, folder, kb_id: str = KB1, update: bool = False) -> Dict[str, Any]:
    results = []
    for path in sorted(Path(folder).rglob("*.pdf")):
        try:
            results.append({"path": str(path), **load_pdf(store, path, kb_id=kb_id, update=update)})
        except Exception as exc:
            results.append({"path": str(path), "error": str(exc)})
    return {"loaded": results, "stats": store.stats(kb_id)}
