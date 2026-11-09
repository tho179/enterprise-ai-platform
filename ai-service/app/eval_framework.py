"""Evaluation of the RAG / GraphRAG pipeline against a labelled question set.

What is measured, and how:
- Retrieval (Recall@k, MRR): rank of the first labelled gold chunk among the
  candidates, before the answer gate. Questions without gold chunks are left
  out of these averages instead of being guessed from text overlap.
- Citation hit rate: at least one cited chunk is a gold chunk.
- Fact recall: share of the labelled key facts present in the answer.
- Refusal: out-of-scope questions must be refused, in-scope ones must not.
- Faithfulness / relevance / correctness: scored by an LLM judge when one is
  configured. `scoring_method` records which scorer produced them; the token
  overlap fallback is a rough proxy and must not be reported as a judge score.

Each `EvalConfig` runs the real pipeline: `architecture` selects flat_rag
(vector), graph_rag (Neo4j) or hybrid_rag (RRF of both).
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from app.config import settings
from app.embedding_service import fold_text
from app.llm_client import LLM, chat_completion, parse_json_object, resolve_llm

logger = logging.getLogger(__name__)

OUT_OF_SCOPE = "out_of_scope"
RETRIEVAL_DEPTH = 10

JUDGE_PROMPT = """Bạn là giám khảo chấm hệ thống hỏi đáp tài liệu. Chấm từng tiêu chí từ 0.0 đến 1.0:
- faithfulness: mọi thông tin trong CÂU TRẢ LỜI đều có trong NGỮ CẢNH.
- relevance: CÂU TRẢ LỜI trả lời đúng trọng tâm CÂU HỎI.
- correctness: CÂU TRẢ LỜI khớp với ĐÁP ÁN CHUẨN.
Chỉ trả về JSON: {"faithfulness": 0.0, "relevance": 0.0, "correctness": 0.0}"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class EvalConfig:
    """The settings an evaluation run actually applies."""
    architecture: str = "hybrid_rag"  # flat_rag | graph_rag | hybrid_rag
    use_reranker: bool = True
    graph_weight: float = settings.GRAPH_RRF_WEIGHT
    top_k: int = 3
    use_llm: bool = True
    run_name: str = "default_eval_run"
    description: str = ""
    # Recorded so a result file says what produced it.
    embedding_model: str = settings.EMBEDDING_MODEL
    reranker_model: str = settings.RERANKER_MODEL
    domain_rules: bool = field(default_factory=lambda: settings.ANSWER_DOMAIN_RULES)
    created_at: str = field(default_factory=_now)


@dataclass
class QuestionEvalResult:
    question_id: str
    question: str
    ground_truth: str
    predicted_answer: str
    category: str
    model_used: str
    retrieved_chunk_ids: List[str]
    cited_chunk_ids: List[str]
    gold_chunk_ids: List[str]
    retrieval_rank: int  # 1-based; 0 = not retrieved
    citation_hit: bool
    fact_recall: Optional[float]
    refused: bool
    faithfulness: float
    answer_relevance: float
    correctness: Optional[float]
    scoring_method: str
    latency_ms: float
    is_passed: bool


@dataclass
class EvalSummary:
    run_id: str
    config: EvalConfig
    total_questions: int
    passed_count: int
    pass_rate: float
    labelled_questions: int
    mrr: float
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    recall_at_10: float
    citation_hit_rate: float
    avg_fact_recall: float
    refusal_accuracy: Optional[float]
    false_refusal_rate: float
    avg_faithfulness: float
    avg_answer_relevance: float
    avg_correctness: Optional[float]
    scoring_method: str
    avg_latency_ms: float
    completed_at: str
    questions: List[QuestionEvalResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[0-9a-z]+", fold_text(text or ""))
    stopwords = {
        "la", "cua", "co", "va", "duoc", "bao", "nhieu", "gi", "nao", "the",
        "khi", "cho", "trong", "mot", "cac", "nhung", "nay", "do", "de", "voi",
        "hay", "hoac", "thi", "ma", "o", "ra", "vao", "len", "xuong", "da", "se",
    }
    return {token for token in tokens if len(token) > 1 and token not in stopwords}


def _mean(values: Sequence[float]) -> float:
    return round(sum(values) / len(values), 4) if values else 0.0


def rank_of_first_gold(retrieved: Sequence[str], gold: Sequence[str]) -> int:
    gold_set = set(gold)
    for rank, chunk_id in enumerate(retrieved, 1):
        if chunk_id in gold_set:
            return rank
    return 0


def fact_recall(answer: str, facts: Sequence[str]) -> Optional[float]:
    """Share of key facts in the answer; accent- and case-insensitive."""
    if not facts:
        return None
    folded = fold_text(answer)
    return round(sum(1 for fact in facts if fold_text(fact) in folded) / len(facts), 4)


class RAGEvaluator:
    def __init__(self, rag_service=None, judge: Optional[LLM] = None):
        self.rag_service = rag_service
        self.judge = judge

    @staticmethod
    def with_configured_judge(rag_service) -> "RAGEvaluator":
        return RAGEvaluator(rag_service=rag_service, judge=resolve_llm())

    def score_faithfulness(self, answer: str, context_chunks: List[str]) -> float:
        answer_tokens = _tokenize(answer)
        if not answer_tokens:
            return 0.0
        context = set().union(*(_tokenize(chunk) for chunk in context_chunks)) if context_chunks else set()
        return round(len(answer_tokens & context) / len(answer_tokens), 4)

    def score_answer_relevance(self, question: str, answer: str) -> float:
        question_tokens = _tokenize(question)
        answer_tokens = _tokenize(answer)
        if not question_tokens or not answer_tokens:
            return 0.0
        overlap = question_tokens & answer_tokens
        return round(min(1.0, len(overlap) / max(1, len(question_tokens) * 0.5)), 4)

    def judge_answer(
        self, question: str, ground_truth: str, answer: str, context: List[str]
    ) -> Optional[Dict[str, float]]:
        if self.judge is None:
            return None
        try:
            raw = chat_completion(
                self.judge,
                [
                    {"role": "system", "content": JUDGE_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            f"NGỮ CẢNH:\n{chr(10).join(context)}\n\nCÂU HỎI:\n{question}\n\n"
                            f"ĐÁP ÁN CHUẨN:\n{ground_truth}\n\nCÂU TRẢ LỜI:\n{answer}"
                        ),
                    },
                ],
                temperature=0.0,
                max_tokens=80,
            )
        except Exception as exc:
            logger.warning("LLM judge failed: %s", exc)
            return None
        scores = parse_json_object(raw)
        try:
            return {
                key: max(0.0, min(1.0, float(scores[key])))
                for key in ("faithfulness", "relevance", "correctness")
            }
        except (TypeError, KeyError, ValueError):
            logger.warning("LLM judge returned no usable scores: %r", raw[:160])
            return None

    def evaluate_item(self, item: Dict[str, Any], config: EvalConfig) -> QuestionEvalResult:
        question = item.get("question", "")
        ground_truth = item.get("ground_truth", "")
        category = item.get("category", "general")
        gold = list(item.get("gold_chunk_ids") or [])
        facts = list(item.get("answer_facts") or [])
        out_of_scope = category == OUT_OF_SCOPE

        started = time.time()
        response = self.rag_service.ask(
            query=question,
            top_k=config.top_k,
            retrieval_mode=config.architecture,
            use_reranker=config.use_reranker,
            graph_weight=config.graph_weight,
            include_retrieval=True,
            use_llm=config.use_llm,
        )
        latency_ms = round((time.time() - started) * 1000, 2)

        answer = response.answer
        cited_ids = [citation.chunk_id for citation in response.citations]
        cited_texts = [citation.snippet for citation in response.citations]
        retrieved_ids = list(response.retrieved_chunk_ids or [])
        refused = not cited_ids

        rank = rank_of_first_gold(retrieved_ids, gold)
        citation_hit = bool(set(cited_ids) & set(gold))
        recall_of_facts = None if refused and out_of_scope else fact_recall(answer, facts)

        judged = None if refused else self.judge_answer(question, ground_truth, answer, cited_texts)
        if judged is not None:
            faithfulness = judged["faithfulness"]
            relevance = judged["relevance"]
            correctness: Optional[float] = judged["correctness"]
            method = "llm_judge"
        else:
            faithfulness = self.score_faithfulness(answer, cited_texts) if not refused else 0.0
            relevance = self.score_answer_relevance(question, answer) if not refused else 0.0
            correctness = None
            method = "token_overlap"

        if out_of_scope:
            passed = refused
        else:
            passed = citation_hit and not refused and (recall_of_facts is None or recall_of_facts >= 1.0)

        return QuestionEvalResult(
            question_id=item.get("id", "q_unknown"),
            question=question,
            ground_truth=ground_truth,
            predicted_answer=answer,
            category=category,
            model_used=response.model_used,
            retrieved_chunk_ids=retrieved_ids,
            cited_chunk_ids=cited_ids,
            gold_chunk_ids=gold,
            retrieval_rank=rank,
            citation_hit=citation_hit,
            fact_recall=recall_of_facts,
            refused=refused,
            faithfulness=faithfulness,
            answer_relevance=relevance,
            correctness=correctness,
            scoring_method=method,
            latency_ms=latency_ms,
            is_passed=passed,
        )

    def evaluate_benchmark(
        self,
        questions: List[Dict[str, Any]],
        config: Optional[EvalConfig] = None,
    ) -> EvalSummary:
        config = config or EvalConfig()
        results = [self.evaluate_item(item, config) for item in questions]

        in_scope = [r for r in results if r.category != OUT_OF_SCOPE]
        out_of_scope = [r for r in results if r.category == OUT_OF_SCOPE]
        labelled = [r for r in in_scope if r.gold_chunk_ids]
        answered = [r for r in results if not r.refused]
        judged = [r for r in answered if r.scoring_method == "llm_judge"]

        def recall_at(k: int) -> float:
            return _mean([1.0 if 0 < r.retrieval_rank <= k else 0.0 for r in labelled])

        total = len(results)
        passed = sum(1 for r in results if r.is_passed)
        if not answered:
            method = "none"
        elif len(judged) == len(answered):
            method = "llm_judge"
        else:
            method = "mixed" if judged else "token_overlap"

        return EvalSummary(
            run_id=f"eval_{int(time.time())}",
            config=config,
            total_questions=total,
            passed_count=passed,
            pass_rate=round(passed / total, 4) if total else 0.0,
            labelled_questions=len(labelled),
            mrr=_mean([1.0 / r.retrieval_rank if r.retrieval_rank else 0.0 for r in labelled]),
            recall_at_1=recall_at(1),
            recall_at_3=recall_at(3),
            recall_at_5=recall_at(5),
            recall_at_10=recall_at(10),
            citation_hit_rate=_mean([1.0 if r.citation_hit else 0.0 for r in labelled]),
            avg_fact_recall=_mean([r.fact_recall for r in in_scope if r.fact_recall is not None]),
            refusal_accuracy=_mean([1.0 if r.refused else 0.0 for r in out_of_scope]) if out_of_scope else None,
            false_refusal_rate=_mean([1.0 if r.refused else 0.0 for r in in_scope]),
            avg_faithfulness=_mean([r.faithfulness for r in answered]),
            avg_answer_relevance=_mean([r.answer_relevance for r in answered]),
            avg_correctness=_mean([r.correctness for r in judged]) if judged else None,
            scoring_method=method,
            avg_latency_ms=_mean([r.latency_ms for r in results]),
            completed_at=_now(),
            questions=results,
        )

    def compare_architectures(
        self,
        questions: List[Dict[str, Any]],
        configs: List[EvalConfig],
    ) -> List[EvalSummary]:
        return [self.evaluate_benchmark(questions, config) for config in configs]
