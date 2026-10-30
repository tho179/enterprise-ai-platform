"""
Re-embed existing Qdrant points with the current embedding pipeline
(fold normalization). Chạy 1 lần sau khi đổi cách nhúng để thay vector cũ.

Cách dùng (trong container ai-service):
    python scripts/09_reembed_normalized.py            # tất cả điểm
    python scripts/09_reembed_normalized.py <DOC_ID>   # 1 tài liệu
"""
import json
import sys

import httpx

from app.embedding_service import EmbeddingService
from app.qdrant_service import QdrantService

QDRANT_BASE = "http://qdrant:6333"
BATCH = 64


def main() -> None:
    doc_id = sys.argv[1] if len(sys.argv) > 1 else None

    qdrant = QdrantService()
    collection = qdrant.collection_name

    body = {"limit": 1024, "with_payload": True, "with_vector": False}
    if doc_id:
        body["filter"] = {"must": [{"key": "document_id", "match": {"value": doc_id}}]}
    r = httpx.post(
        f"{QDRANT_BASE}/collections/{collection}/points/scroll",
        content=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    points = json.loads(r.content)["result"]["points"]
    if not points:
        print("No points found; nothing to do.")
        return

    embedder = EmbeddingService()
    batch = []
    for point in points:
        content = point["payload"].get("content", "")
        vector = embedder.embed_query(content)
        batch.append({
            "id": point["id"],
            "vector": vector,
            "payload": point["payload"],
        })
        if len(batch) >= BATCH:
            upsert(collection, batch)
            batch = []

    if batch:
        upsert(collection, batch)
    print(f"Re-embedded {len(points)} points into '{collection}'.")


def upsert(collection: str, batch: list) -> None:
    r = httpx.put(
        f"{QDRANT_BASE}/collections/{collection}/points?wait=true",
        content=json.dumps({"points": batch}, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json"},
    )
    r.raise_for_status()


if __name__ == "__main__":
    main()
