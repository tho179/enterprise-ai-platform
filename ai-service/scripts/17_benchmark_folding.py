"""Does removing Vietnamese accents before embedding help retrieval?

Embeds the indexed chunks and labelled questions twice with the configured
model, once folded and once with accents kept, and ranks by cosine alone.

    docker compose exec ai-service python scripts/17_benchmark_folding.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
from qdrant_client import QdrantClient  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

from app.config import settings  # noqa: E402
from app.embedding_service import fold_text  # noqa: E402
from app.eval_framework import rank_of_first_gold  # noqa: E402


def scroll_chunks():
    client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY or None, timeout=30.0)
    chunks, offset = [], None
    while True:
        points, offset = client.scroll(
            settings.QDRANT_COLLECTION, limit=256, offset=offset, with_payload=True, with_vectors=False
        )
        chunks += [(point.payload["chunk_id"], point.payload["content"]) for point in points]
        if offset is None:
            return chunks


def evaluate(model, chunks, questions, prepare):
    ids = [chunk_id for chunk_id, _ in chunks]
    passages = model.encode(
        [settings.EMBEDDING_PASSAGE_PREFIX + prepare(text) for _, text in chunks],
        batch_size=32,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    ranks = []
    for item in questions:
        query = model.encode(
            settings.EMBEDDING_QUERY_PREFIX + prepare(item["question"]), normalize_embeddings=True
        )
        order = np.argsort(-(passages @ query))
        ranks.append(rank_of_first_gold([ids[index] for index in order], item["gold_chunk_ids"]))
    total = len(ranks)
    return {
        "mrr": round(sum(1 / rank for rank in ranks if rank) / total, 4),
        **{f"recall_at_{k}": round(sum(1 for rank in ranks if 0 < rank <= k) / total, 4) for k in (1, 3, 5, 10)},
        "questions": total,
    }


def main() -> int:
    questions = [
        item
        for item in json.loads((ROOT / "data/eval/eval_questions.json").read_text(encoding="utf-8"))
        if item.get("gold_chunk_ids")
    ]
    chunks = scroll_chunks()
    model = SentenceTransformer(settings.EMBEDDING_MODEL)
    results = {
        "model": settings.EMBEDDING_MODEL,
        "chunks": len(chunks),
        "folded": evaluate(model, chunks, questions, fold_text),
        "accented": evaluate(model, chunks, questions, lambda text: " ".join(text.split())),
    }
    output = ROOT / "data/eval/results/embedding_folding.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
