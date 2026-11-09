import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.eval_framework import (
    EvalConfig,
    RAGEvaluator,
    _tokenize,
    fact_recall,
    rank_of_first_gold,
)

from app.llm_client import LLM


def fake_rag(citations=("answer",), answer="HĐQT gồm 03 đến 11 thành viên.", retrieved=("noise", "answer")):
    rag = MagicMock()
    rag.ask.return_value = SimpleNamespace(
        answer=answer,
        model_used="fake",
        citations=[SimpleNamespace(chunk_id=c, snippet=answer) for c in citations],
        retrieved_chunk_ids=list(retrieved),
    )
    return rag


ITEM = {
    "id": "q1",
    "question": "HĐQT có bao nhiêu thành viên?",
    "ground_truth": "HĐQT gồm 03 đến 11 thành viên.",
    "category": "count",
    "gold_chunk_ids": ["answer"],
    "answer_facts": ["03", "11"],
}
OUT_OF_SCOPE_ITEM = {
    "id": "q2",
    "question": "Cách làm bánh pizza?",
    "ground_truth": "",
    "category": "out_of_scope",
}


class TestEvalFramework(unittest.TestCase):
    def test_tokenize_vietnamese(self):
        tokens = _tokenize("Hội đồng Quản trị họp ít nhất mỗi quý một lần")
        self.assertIn("hoi", tokens)
        self.assertNotIn("mot", tokens)

    def test_rank_uses_gold_ids_not_text_similarity(self):
        self.assertEqual(rank_of_first_gold(["a", "b"], ["b"]), 2)
        self.assertEqual(rank_of_first_gold(["a"], ["b"]), 0)

    def test_fact_recall_ignores_accents(self):
        self.assertEqual(fact_recall("nhiem ky 05 NĂM", ["05 năm", "bầu lại"]), 0.5)
        self.assertIsNone(fact_recall("x", []))

    def test_architecture_and_flags_reach_the_pipeline(self):
        rag = fake_rag()
        config = EvalConfig(architecture="graph_rag", use_reranker=False, graph_weight=0.7, use_llm=False)

        RAGEvaluator(rag_service=rag).evaluate_item(ITEM, config)

        kwargs = rag.ask.call_args.kwargs
        self.assertEqual(kwargs["retrieval_mode"], "graph_rag")
        self.assertFalse(kwargs["use_reranker"])
        self.assertEqual(kwargs["graph_weight"], 0.7)
        self.assertFalse(kwargs["use_llm"])
        self.assertTrue(kwargs["include_retrieval"])

    def test_passes_only_with_gold_citation_and_all_facts(self):
        evaluator = RAGEvaluator(rag_service=fake_rag())
        result = evaluator.evaluate_item(ITEM, EvalConfig())
        self.assertEqual(result.retrieval_rank, 2)
        self.assertTrue(result.is_passed)

        wrong_chunk = RAGEvaluator(rag_service=fake_rag(citations=("noise",)))
        self.assertFalse(wrong_chunk.evaluate_item(ITEM, EvalConfig()).is_passed)

        missing_fact = RAGEvaluator(rag_service=fake_rag(answer="HĐQT gồm 03 thành viên."))
        self.assertFalse(missing_fact.evaluate_item(ITEM, EvalConfig()).is_passed)

    def test_out_of_scope_passes_only_when_refused(self):
        refused = RAGEvaluator(rag_service=fake_rag(citations=(), answer="chưa tìm thấy"))
        self.assertTrue(refused.evaluate_item(OUT_OF_SCOPE_ITEM, EvalConfig()).is_passed)

        answered = RAGEvaluator(rag_service=fake_rag())
        self.assertFalse(answered.evaluate_item(OUT_OF_SCOPE_ITEM, EvalConfig()).is_passed)

    def test_summary_separates_retrieval_from_refusal(self):
        rag = MagicMock()
        rag.ask.side_effect = [
            fake_rag().ask.return_value,
            fake_rag(citations=(), answer="chưa tìm thấy", retrieved=("noise",)).ask.return_value,
        ]
        summary = RAGEvaluator(rag_service=rag).evaluate_benchmark([ITEM, OUT_OF_SCOPE_ITEM], EvalConfig())

        self.assertEqual(summary.labelled_questions, 1)
        self.assertEqual(summary.mrr, 0.5)
        self.assertEqual(summary.recall_at_1, 0.0)
        self.assertEqual(summary.recall_at_3, 1.0)
        self.assertEqual(summary.refusal_accuracy, 1.0)
        self.assertEqual(summary.false_refusal_rate, 0.0)
        self.assertEqual(summary.scoring_method, "token_overlap")
        self.assertIsNone(summary.avg_correctness)

    def test_llm_judge_scores_are_labelled(self):
        message = SimpleNamespace(content='{"faithfulness": 1, "relevance": 0.5, "correctness": 2}')
        judge = LLM(
            model="judge",
            provider="test",
            client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
                create=lambda **_: SimpleNamespace(choices=[SimpleNamespace(message=message)])
            ))),
        )
        result = RAGEvaluator(rag_service=fake_rag(), judge=judge).evaluate_item(ITEM, EvalConfig())
        self.assertEqual(result.scoring_method, "llm_judge")
        self.assertEqual(result.answer_relevance, 0.5)
        self.assertEqual(result.correctness, 1.0)  # clamped

    def test_unusable_judge_reply_falls_back_to_labelled_overlap(self):
        message = SimpleNamespace(content="không chấm được")
        judge = LLM(
            model="judge",
            provider="test",
            client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
                create=lambda **_: SimpleNamespace(choices=[SimpleNamespace(message=message)])
            ))),
        )
        result = RAGEvaluator(rag_service=fake_rag(), judge=judge).evaluate_item(ITEM, EvalConfig())
        self.assertEqual(result.scoring_method, "token_overlap")
        self.assertIsNone(result.correctness)


if __name__ == "__main__":
    unittest.main()
