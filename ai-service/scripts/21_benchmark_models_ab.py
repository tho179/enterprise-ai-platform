"""Model A vs model AB: does adding a cross-encoder (B) to each bi-encoder (A) pay off?

A  = bi-encoder only: cosine between question and chunk embeddings.
AB = A retrieves the top RERANK_DEPTH chunks, then the cross-encoder reorders them.

Run on the indexed corpus (Qdrant chunks of the 7 uploaded documents) with the
18 labelled questions of data/eval/eval_questions.json, so every model sees the
same chunks, the same questions and the same gold labels.

  docker compose exec -e HF_HUB_OFFLINE=1 ai-service python scripts/21_benchmark_models_ab.py

Writes data/eval/results/models_ab.json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
from sentence_transformers import CrossEncoder, SentenceTransformer  # noqa: E402

from app.config import settings  # noqa: E402
from app.eval_framework import rank_of_first_gold  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
from importlib import import_module  # noqa: E402

scroll_chunks = import_module("17_benchmark_folding").scroll_chunks

# (name, Hugging Face id, query prefix, passage prefix)
MODELS = [
    ("MiniLM-L12 (đa ngữ)", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", "", ""),
    ("BKAI Vietnamese bi-encoder", "bkai-foundation-models/vietnamese-bi-encoder", "", ""),
    ("Multilingual-E5-Small", "intfloat/multilingual-e5-small", "query: ", "passage: "),
    ("Multilingual-E5-Base", "intfloat/multilingual-e5-base", "query: ", "passage: "),
]
RERANK_DEPTH = 20
QUESTIONS = ROOT / "data/eval/eval_questions.json"
OUT = ROOT / "data/eval/results/models_ab.json"


def metrics(ranks):
    """ranks are 1-based (rank_of_first_gold); 0 means the gold chunk was not found."""
    n = len(ranks)
    return {
        "mrr": round(sum(1 / r for r in ranks if r > 0) / n, 4),
        "recall_at_1": round(sum(1 <= r <= 1 for r in ranks) / n, 4),
        "recall_at_3": round(sum(1 <= r <= 3 for r in ranks) / n, 4),
        "recall_at_10": round(sum(1 <= r <= 10 for r in ranks) / n, 4),
    }


def main() -> int:
    questions = [
        q for q in json.loads(QUESTIONS.read_text(encoding="utf-8")) if q.get("gold_chunk_ids")
    ]
    chunks = scroll_chunks()
    ids = [chunk_id for chunk_id, _ in chunks]
    texts = [" ".join(content.split()) for _, content in chunks]
    reranker = CrossEncoder(settings.RERANKER_MODEL, max_length=512)
    print(f"{len(questions)} questions, {len(chunks)} chunks, reranker {settings.RERANKER_MODEL}")

    rows = []
    for name, model_id, query_prefix, passage_prefix in MODELS:
        model = SentenceTransformer(model_id)
        started = time.time()
        passages = model.encode([passage_prefix + t for t in texts], normalize_embeddings=True,
                                batch_size=32, show_progress_bar=False)
        index_s = time.time() - started

        ranks_a, ranks_ab, ms_a, ms_ab = [], [], [], []
        for item in questions:
            t0 = time.time()
            vector = model.encode(query_prefix + item["question"], normalize_embeddings=True)
            order = np.argsort(-(passages @ vector))
            ranked = [ids[i] for i in order]
            ms_a.append((time.time() - t0) * 1000)
            ranks_a.append(rank_of_first_gold(ranked, item["gold_chunk_ids"]))

            t1 = time.time()
            head = list(order[:RERANK_DEPTH])
            scores = reranker.predict(
                [(item["question"], texts[i][: settings.RERANK_PASSAGE_CHARS]) for i in head],
                show_progress_bar=False,
            )
            reordered = [ids[head[j]] for j in np.argsort(-np.asarray(scores))] + ranked[RERANK_DEPTH:]
            ms_ab.append(ms_a[-1] + (time.time() - t1) * 1000)
            ranks_ab.append(rank_of_first_gold(reordered, item["gold_chunk_ids"]))

        row = {
            "model": name,
            "hf_id": model_id,
            "dimensions": int(passages.shape[1]),
            "parameters_m": round(sum(p.numel() for p in model.parameters()) / 1e6, 1),
            "index_seconds": round(index_s, 1),
            "A": {**metrics(ranks_a), "ms_per_query": round(float(np.mean(ms_a)), 1)},
            "AB": {**metrics(ranks_ab), "ms_per_query": round(float(np.mean(ms_ab)), 1)},
        }
        rows.append(row)
        print(f"| {name} | {row['dimensions']} | A: {row['A']} | AB: {row['AB']} |", flush=True)

    OUT.write_text(json.dumps({
        "questions": len(questions), "chunks": len(chunks), "rerank_depth": RERANK_DEPTH,
        "reranker": settings.RERANKER_MODEL, "results": rows,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
