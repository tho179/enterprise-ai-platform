"""Run the labelled benchmark across retrieval architectures.

    docker compose exec ai-service python scripts/15_run_eval.py [--with-llm]

Writes one JSON per configuration to data/eval/results/ and prints a table.
Runs without --with-llm use extractive answers, so retrieval and answer-policy
differences are not mixed with LLM wording.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.eval_framework import EvalConfig, RAGEvaluator  # noqa: E402
from app.llm_client import resolve_llm  # noqa: E402
from app.rag_service import RAGService  # noqa: E402

QUESTIONS = ROOT / "data/eval/eval_questions.json"
RESULTS = ROOT / "data/eval/results"

COLUMNS = [
    ("MRR", "mrr"),
    ("R@1", "recall_at_1"),
    ("R@3", "recall_at_3"),
    ("R@5", "recall_at_5"),
    ("Cite", "citation_hit_rate"),
    ("Facts", "avg_fact_recall"),
    ("Refuse", "refusal_accuracy"),
    ("FalseRef", "false_refusal_rate"),
    ("Pass", "pass_rate"),
    ("ms", "avg_latency_ms"),
]


def run(rag, questions, name, judge=None, domain_rules=True, **config):
    settings.ANSWER_DOMAIN_RULES = domain_rules
    summary = RAGEvaluator(rag_service=rag, judge=judge).evaluate_benchmark(
        questions, EvalConfig(run_name=name, **config)
    )
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / f"{name}.json").write_text(
        json.dumps(summary.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"| {name} | " + " | ".join(str(getattr(summary, key)) for _, key in COLUMNS) + " |",
        flush=True,
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--with-llm", action="store_true", help="also run generation and the LLM judge")
    parser.add_argument("--llm-only", action="store_true", help="skip the retrieval matrix")
    args = parser.parse_args()

    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    rag = RAGService()
    print("| Run | " + " | ".join(title for title, _ in COLUMNS) + " |")
    print("|---|" + "---|" * len(COLUMNS), flush=True)

    for domain_rules, suffix in () if args.llm_only else ((True, "rules"), (False, "generic")):
        for architecture in ("flat_rag", "graph_rag", "hybrid_rag"):
            run(
                rag,
                questions,
                f"{architecture}_{suffix}",
                domain_rules=domain_rules,
                architecture=architecture,
                use_llm=False,
            )
    if not args.llm_only:
        run(rag, questions, "hybrid_rag_no_reranker", architecture="hybrid_rag", use_reranker=False, use_llm=False)

    if args.with_llm or args.llm_only:
        judge = resolve_llm()
        if judge is None:
            print("No LLM configured; skipping the generation run.", file=sys.stderr)
            return 1
        summary = run(
            rag, questions, "hybrid_rag_llm", judge=judge, domain_rules=False, architecture="hybrid_rag", use_llm=True
        )
        print(
            f"\nLLM judge ({judge.model}, {summary.scoring_method}): "
            f"faithfulness={summary.avg_faithfulness} relevance={summary.avg_answer_relevance} "
            f"correctness={summary.avg_correctness}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
