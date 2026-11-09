"""CLI: backfill Neo4j from the chunks already stored in Qdrant.

Run once after enabling graph sync so existing uploads become graph-searchable
without re-uploading. New uploads sync automatically in /api/v1/ingest.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from qdrant_client import QdrantClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.knowledge_graph.pipeline import KB  # noqa: E402
from app.knowledge_graph.service import get_store, sync_ingest_chunks  # noqa: E402


def main() -> int:
    client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None, timeout=10.0)
    chunks = []
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            limit=256,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in points:
            payload = dict(point.payload or {})
            metadata = {
                key: value
                for key, value in payload.items()
                if key not in ("chunk_id", "content")
            }
            chunks.append(
                {
                    "chunk_id": payload.get("chunk_id") or str(point.id),
                    "content": payload.get("content", ""),
                    "metadata": metadata,
                }
            )
        if offset is None:
            break

    synced = sync_ingest_chunks(chunks, force=True)
    stats = get_store().stats(KB)
    print(
        f"Qdrant points: {len(chunks)} | graph chunks synced: {synced} | "
        f"Neo4j documents: {stats.get('documents', 0)}, "
        f"chunks: {stats.get('chunks', 0)}, entities: {stats.get('entities', 0)}, "
        f"relationships: {stats.get('relationships', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
