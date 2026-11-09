"""Re-embed every Qdrant point with the current EMBEDDING_MODEL.

Run after changing the embedding model or its query/passage prefixes. The
collection dimension must stay the same (E5-small and MiniLM are both 384).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from qdrant_client import QdrantClient  # noqa: E402
from qdrant_client.models import PointStruct  # noqa: E402

from app.config import settings  # noqa: E402
from app.embedding_service import EmbeddingService  # noqa: E402


def main() -> int:
    client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None, timeout=30.0)
    points = []
    offset = None
    while True:
        batch, offset = client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            limit=128,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        points.extend(batch)
        if offset is None:
            break

    if not points:
        print("Qdrant collection is empty; nothing to re-embed.")
        return 0

    embedder = EmbeddingService()
    vectors = embedder.embed_documents([p.payload.get("content", "") for p in points])
    for start in range(0, len(points), 64):
        client.upsert(
            collection_name=settings.QDRANT_COLLECTION,
            points=[
                PointStruct(
                    id=point.id,
                    vector=vector,
                    payload=point.payload,
                )
                for point, vector in zip(
                    points[start:start + 64],
                    vectors[start:start + 64],
                )
            ],
            wait=True,
        )

    print(
        f"Re-embedded {len(points)} Qdrant points with {embedder.model_name} "
        f"({embedder.vector_dim} dims)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
