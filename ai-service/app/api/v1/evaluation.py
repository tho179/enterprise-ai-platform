"""
Evaluation API Router
Provides endpoints to run benchmarks, inspect datasets, and compare architectures.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.api.v1.chat import get_rag_service
from app.config import settings
from app.eval_framework import EvalConfig, RAGEvaluator

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/eval", tags=["Model Evaluation & Benchmarking"])

EVAL_DATASET_PATH = Path("data/eval/eval_questions.json")


class EvalConfigRequest(BaseModel):
    architecture: Literal["flat_rag", "graph_rag", "hybrid_rag"] = "hybrid_rag"
    use_reranker: bool = True
    graph_weight: float = settings.GRAPH_RRF_WEIGHT
    top_k: int = Field(default=3, ge=1, le=10)
    use_llm: bool = True
    run_name: str = "api_eval_run"
    description: str = "Benchmark run via API"


class RunEvalRequest(BaseModel):
    config: Optional[EvalConfigRequest] = None
    questions: Optional[List[Dict[str, Any]]] = None


def _load_default_questions() -> List[Dict[str, Any]]:
    if not EVAL_DATASET_PATH.exists():
        return []
    with open(EVAL_DATASET_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/questions", summary="Get standard benchmark questions")
def get_benchmark_questions():
    questions = _load_default_questions()
    return {
        "success": True,
        "total": len(questions),
        "data": questions
    }


@router.post("/run", summary="Execute evaluation run on benchmark dataset")
def run_evaluation(payload: RunEvalRequest):
    questions = payload.questions or _load_default_questions()
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No questions provided and default dataset is missing."
        )

    cfg = EvalConfig(**payload.config.model_dump()) if payload.config else EvalConfig()
    evaluator = RAGEvaluator.with_configured_judge(get_rag_service())
    summary = evaluator.evaluate_benchmark(questions, cfg)

    return {
        "success": True,
        "data": summary.to_dict()
    }


@router.post("/compare", summary="Compare multiple architectures (flat_rag vs graph_rag vs hybrid_rag)")
def compare_architectures(configs: List[EvalConfigRequest]):
    questions = _load_default_questions()
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Benchmark questions dataset is empty or not found."
        )

    evaluator = RAGEvaluator.with_configured_judge(get_rag_service())
    eval_configs = [EvalConfig(**config.model_dump()) for config in configs]

    summaries = evaluator.compare_architectures(questions, eval_configs)
    return {
        "success": True,
        "total_configs": len(summaries),
        "data": [s.to_dict() for s in summaries]
    }

