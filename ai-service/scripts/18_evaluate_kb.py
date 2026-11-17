"""Evaluate the knowledge base itself, separately from RAG answer quality.

  docker compose exec ai-service python scripts/18_evaluate_kb.py
  docker compose exec ai-service python scripts/18_evaluate_kb.py --sample 15

Two kinds of measurement:
  1. Label-free structural metrics (06_quality.cypher): size, coverage,
     integrity, consistency, certainty, freshness.
  2. Extraction precision from a stratified sample of MENTIONS edges. The
     sample is written to data/eval/kb_entity_sample.json with "correct": null;
     a reviewer fills true/false and re-runs the script to get precision per
     extraction method. Existing labels are kept when the sample is redrawn.

Writes data/eval/results/kb_quality.json.
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.knowledge_graph.extract import ENGLISH_ALIASES, ENTITY_ALIASES  # noqa: E402
from app.knowledge_graph.ids import fold  # noqa: E402
from app.knowledge_graph.service import get_store  # noqa: E402

SAMPLE = ROOT / "data/eval/kb_entity_sample.json"
OUT = ROOT / "data/eval/results/kb_quality.json"

MENTIONS = """
MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)-[m:MENTIONS]->(e:Entity)
WHERE coalesce(d.is_current, true) AND d.duplicate_of IS NULL
RETURN c.chunk_id AS chunk_id, d.title AS title, c.text AS text,
       e.entity_id AS entity_id, e.name AS name, e.type AS type,
       m.method AS method, m.confidence AS confidence
"""


def snippet(text: str, name: str, width: int = 140) -> str:
    """Text around the first surface form of the entity, for the reviewer."""
    forms = [name]
    if name in ENTITY_ALIASES:
        forms += ENTITY_ALIASES[name][1]
    forms += ENGLISH_ALIASES.get(name, [])
    folded = fold(text)
    flat = re.sub(r"\s+", " ", text)
    for form in forms:
        position = folded.find(fold(form))
        if position >= 0:
            start = max(0, position - width)
            return ("…" if start else "") + flat[start:position + len(form) + width] + "…"
    return flat[: 2 * width] + "…"


def draw_sample(rows, per_method: int, seed: int):
    by_method = defaultdict(list)
    for row in rows:
        by_method[row["method"] or "unknown"].append(row)
    rng = random.Random(seed)
    sample = []
    for method in sorted(by_method):
        items = by_method[method]
        for row in rng.sample(items, min(per_method, len(items))):
            sample.append(
                {
                    "key": f"{row['chunk_id']}|{row['entity_id']}",
                    "method": method,
                    "confidence": row["confidence"],
                    "entity": row["name"],
                    "type": row["type"],
                    "document": row["title"],
                    "context": snippet(row["text"] or "", row["name"]),
                    "correct": None,
                }
            )
    return sample, {method: len(items) for method, items in by_method.items()}


def precision(sample, population):
    """Per-method precision and the population-weighted overall estimate."""
    per_method = {}
    for method in sorted({item["method"] for item in sample}):
        labelled = [item for item in sample if item["method"] == method and item["correct"] is not None]
        if labelled:
            per_method[method] = {
                "labelled": len(labelled),
                "precision": round(sum(bool(item["correct"]) for item in labelled) / len(labelled), 3),
                "population": population.get(method, 0),
            }
    covered = {m: v for m, v in per_method.items() if v["population"]}
    total = sum(v["population"] for v in covered.values())
    weighted = (
        round(sum(v["precision"] * v["population"] for v in covered.values()) / total, 3) if total else None
    )
    return per_method, weighted


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=int, default=15, help="mentions drawn per extraction method")
    parser.add_argument("--seed", type=int, default=13)
    parser.add_argument("--redraw", action="store_true", help="draw a new sample (labels kept by key)")
    parser.add_argument("--sample-file", help="use another sample file, e.g. a fresh sample after a fix")
    parser.add_argument("--out", help="result file (default data/eval/results/kb_quality.json)")
    args = parser.parse_args()
    global SAMPLE, OUT
    if args.sample_file:
        SAMPLE = ROOT / args.sample_file
    if args.out:
        OUT = ROOT / args.out

    store = get_store()
    quality = store.quality()

    rows = store._run(MENTIONS)
    sample, population = draw_sample(rows, args.sample, args.seed)
    if SAMPLE.exists() and not args.redraw:
        sample = json.loads(SAMPLE.read_text(encoding="utf-8"))
    elif SAMPLE.exists():
        old = {item["key"]: item["correct"] for item in json.loads(SAMPLE.read_text(encoding="utf-8"))}
        for item in sample:
            item["correct"] = old.get(item["key"])
    SAMPLE.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")

    per_method, weighted = precision(sample, population)

    # After an extractor change the sample is not redrawn: each labelled
    # mention is checked again. A wrong mention that disappeared is a fixed
    # false positive; a correct one that disappeared is lost recall.
    existing = {
        f"{row['chunk_id']}|{row['entity_id']}"
        for row in store._run(
            "UNWIND $keys AS key "
            "WITH split(key, '|') AS parts "
            "MATCH (:Chunk {chunk_id: parts[0]})-[:MENTIONS]->(e:Entity {entity_id: parts[1]}) "
            "RETURN parts[0] AS chunk_id, parts[1] AS entity_id",
            keys=[item["key"] for item in sample],
        )
    }
    labelled = [item for item in sample if item["correct"] is not None]
    kept = [item for item in labelled if item["key"] in existing]
    recheck = {
        "labelled": len(labelled),
        "still_extracted": len(kept),
        "fixed_false_positives": sum(not item["correct"] and item["key"] not in existing for item in labelled),
        "lost_true_positives": sum(item["correct"] and item["key"] not in existing for item in labelled),
        "sample_precision_before": round(sum(item["correct"] for item in labelled) / len(labelled), 3) if labelled else None,
        "sample_precision_after": round(sum(item["correct"] for item in kept) / len(kept), 3) if kept else None,
    }
    result = {
        "structure": quality,
        "extraction_precision": {
            "per_method": per_method,
            "weighted_precision": weighted,
            "sample_file": str(SAMPLE.relative_to(ROOT)),
            "unlabelled": sum(item["correct"] is None for item in sample),
            "recheck_after_fix": recheck,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    for name, table in quality.items():
        print(f"\n## {name}")
        for row in table:
            print("  ", row)
    print("\n## Extraction precision")
    for method, values in per_method.items():
        print(f"   {method:14s} {values}")
    print(f"   weighted precision: {weighted}  (unlabelled: {result['extraction_precision']['unlabelled']})")
    print(f"   recheck on the same sample: {recheck}")
    print(f"\nwrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
