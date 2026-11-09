"""Answer policy by question type, with and without the corpus-tuned rules."""
from unittest.mock import patch

import pytest

from app.answer_policy import _answer_shape, _list_windows, select_evidence
from app.config import settings
from app.rag_service import RAGService


@pytest.fixture
def generic_only():
    with patch.object(settings, "ANSWER_DOMAIN_RULES", False):
        yield


class FakeReranker:
    enabled = True

    def __init__(self, score=5.0):
        self.score = score

    def score_pairs(self, query, texts):
        return [self.score for _ in texts]


def hit(chunk_id, content, score=0.8):
    return {"chunk_id": chunk_id, "content": content, "score": score, "metadata": {}}


@pytest.mark.parametrize(
    "question, passage, expected",
    [
        ("Hội đồng có bao nhiêu thành viên?", "Hội đồng có 05 thành viên chính thức.", "count"),
        ("Công ty có bao nhiêu chi nhánh?", "Công ty hiện có 12 chi nhánh trên toàn quốc.", "count"),
        ("Thời gian thử việc tối đa là bao lâu?", "Thời gian thử việc không quá 60 ngày.", "time"),
        ("Tỷ lệ đóng góp của cổ đông là bao nhiêu?", "Cổ đông góp tỷ lệ 35% vốn.", "ratio"),
        ("Điều 12 quy định gì?", "Điều 12. Quyền của nhân viên.", "article"),
    ],
)
def test_shape_accepts_matching_passage_without_domain_rules(generic_only, question, passage, expected):
    assert _answer_shape(question, passage) == expected


@pytest.mark.parametrize(
    "question, passage",
    [
        ("Công ty có bao nhiêu chi nhánh?", "Chi nhánh phải báo cáo định kỳ."),
        ("Điều 12 quy định gì?", "Điều 13. Quyền của nhân viên."),
        ("Tỷ lệ đóng góp của cổ đông là bao nhiêu?", "Cổ đông có quyền dự họp."),
    ],
)
def test_shape_rejects_wrong_kind_of_information(generic_only, question, passage):
    assert _answer_shape(question, passage) is None


def test_word_value_alone_is_not_a_monetary_question(generic_only):
    passage = "Giá trị cốt lõi của công ty là chính trực và trách nhiệm với khách hàng."
    assert _answer_shape("Giá trị cốt lõi của công ty là gì?", passage) == "default"


def test_monetary_value_question_still_needs_a_figure(generic_only):
    question = "Giá trị hợp đồng tối thiểu là bao nhiêu?"
    assert _answer_shape(question, "Hợp đồng phải được lập thành văn bản.") is None


def test_domain_rule_only_applies_when_enabled():
    question = "Công ty có thể cho vay không?"
    passage = "Công ty được cho vay theo hạn mức phải được báo cáo."
    with patch.object(settings, "ANSWER_DOMAIN_RULES", True):
        assert _answer_shape(question, passage) is None


def test_list_window_starts_at_topic_without_hardcoded_heading():
    content = "Phần mở đầu giới thiệu chung. " * 30 + (
        "Tiêu chí đánh giá đối tác gồm: năng lực, giá cả, tiến độ."
    )
    windows = list(_list_windows("Tiêu chí đánh giá đối tác gồm những gì?", content))
    assert windows and windows[0].startswith("Tiêu chí đánh giá đối tác")


def test_select_evidence_refuses_when_topic_is_absent():
    hits = [hit("c1", "Điều lệ quy định cơ cấu tổ chức của công ty.")]
    assert select_evidence("Cách làm bánh pizza hải sản?", hits, 3, FakeReranker()) == []


def test_select_evidence_keeps_answer_window():
    hits = [hit("c1", "Hội đồng Quản trị có từ 03 đến 11 thành viên. Nội dung khác.")]
    selected = select_evidence("Hội đồng Quản trị có bao nhiêu thành viên?", hits, 3, FakeReranker())
    assert [item["chunk_id"] for item in selected] == ["c1"]
    assert "03 đến 11" in selected[0]["answer_window"]


def test_select_evidence_applies_the_rerank_gate_to_open_questions(generic_only):
    hits = [hit("c1", "Chính sách bảo mật mật khẩu áp dụng cho toàn thể nhân viên công ty.")]
    question = "Chính sách bảo mật mật khẩu áp dụng thế nào?"
    assert select_evidence(question, hits, 3, FakeReranker(score=5.0))
    assert select_evidence(question, hits, 3, FakeReranker(score=-20.0)) == []


class _Retriever:
    class embedding:
        @staticmethod
        def embed_query(query):
            return [0.0]

    class reranker:
        enabled = False

    def search(self, **kwargs):
        return [hit("c1", "Hội đồng Quản trị có từ 03 đến 11 thành viên.")]


class _Completions:
    def __init__(self, replies):
        self.replies = list(replies)

    def create(self, **kwargs):
        reply = self.replies.pop(0)
        message = type("M", (), {"content": reply})
        return type("R", (), {"choices": [type("C", (), {"message": message})]})


def _llm(replies):
    from app.llm_client import LLM

    chat = type("Chat", (), {"completions": _Completions(replies)})
    return LLM(client=type("Client", (), {"chat": chat}), model="fake", provider="test")


QUESTION = "Hội đồng Quản trị có bao nhiêu thành viên?"


def _ask(replies):
    service = RAGService(retriever=_Retriever())
    with patch("app.rag_service.resolve_llm", return_value=_llm(replies)):
        return service.ask(QUESTION, retrieval_mode="flat_rag", use_reranker=False)


def test_verified_answer_is_returned():
    response = _ask(["Có từ 03 đến 11 thành viên [1].", '{"supported": true}'])
    assert response.answer.startswith("Có từ 03")
    assert response.verified is True
    assert response.model_used == "fake"
    assert "llm_generate" in response.timings_ms


def test_rejected_answer_falls_back_to_the_verbatim_excerpt():
    response = _ask(["Có đúng 99 thành viên [1].", '{"supported": false}'])
    assert "99" not in response.answer
    assert "03 đến 11" in response.answer
    assert response.verified is False
    assert response.citations


def test_llm_refusal_drops_citations():
    response = _ask(["Dựa trên tài liệu, tôi chưa tìm thấy thông tin để trả lời."])
    assert response.citations == []


def test_unreadable_verdict_keeps_answer_as_unverified():
    response = _ask(["Có từ 03 đến 11 thành viên [1].", "không rõ"])
    assert response.answer.startswith("Có từ 03")
    assert response.verified is None


def test_empty_llm_reply_uses_the_verbatim_excerpt():
    response = _ask([""])
    assert "03 đến 11" in response.answer
    assert response.model_used == "fake-fallback"
    assert response.citations
