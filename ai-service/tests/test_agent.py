"""Rule-based agent: rule order, tool choice, retry and refusal."""
from app.agent import RuleBasedAgent
from app.agent.perception import perceive
from app.agent.rules import RULES, describe
from app.schemas import AskResponse, CitationItem


def _response(query, answered):
    citations = [CitationItem(index=1, chunk_id="c1", score=0.9, pages="Trang 1", snippet="x")] if answered else []
    return AskResponse(query=query, answer="ok" if answered else "refused", citations=citations,
                       execution_time_ms=1.0, model_used="fake", retrieved_chunk_ids=["c1"])


class FakeRAG:
    retriever = None

    def __init__(self, answers):
        self.answers = dict(answers)  # mode -> answered?
        self.calls = []

    def ask(self, query, retrieval_mode, **kwargs):
        self.calls.append(retrieval_mode)
        return _response(query, self.answers.get(retrieval_mode, False))


class FakeStore:
    def __init__(self, rows):
        self.rows = rows

    def attribute_values(self, attribute):
        return self.rows


CAPITAL = [
    {"value": 13074049490000, "status": "accepted", "title": "Dieu le cong ty 2026", "effective_date": "2026-01-01",
     "chunk_id": "a", "document_id": "d26", "text": "Vốn Điều Lệ ...", "page": 3, "page_end": 3, "confidence": 0.9},
    {"value": 10623648220000, "status": "superseded", "title": "Dieu le cong ty 2025", "effective_date": "2025-01-01",
     "chunk_id": "b", "document_id": "d25", "text": "Vốn Điều Lệ ...", "page": 3, "page_end": 3, "confidence": 0.9},
]


def _agent(answers, rows=None, graph=True):
    rag = FakeRAG(answers)
    agent = RuleBasedAgent(rag=rag, store_factory=lambda: FakeStore(rows or []), graph_available=graph)
    return agent, rag


def _rules(response):
    return [step["rule"] for step in response.agent_trace[1:]]


def test_perception_reads_shape_article_attribute_and_entities():
    obs = perceive("Vốn điều lệ hiện nay của công ty là bao nhiêu?")
    assert obs.attribute == "Vốn điều lệ" and obs.shape == "count"
    assert perceive("Điều 15 quy định gì?").article == "15"
    assert "Hội đồng Quản trị" in perceive("HĐQT họp mấy lần một năm?").entities


def test_attribute_question_is_answered_from_the_kb_without_retrieval():
    agent, rag = _agent({}, rows=CAPITAL)
    response = agent.ask("Vốn điều lệ hiện nay là bao nhiêu?")
    assert rag.calls == []
    assert _rules(response) == ["R3_thuoc_tinh_mot_gia_tri", "R4_thuoc_tinh_da_co"]
    assert "13.074.049.490.000 đồng" in response.answer
    assert [c.chunk_id for c in response.citations] == ["a", "b"]


def test_attribute_missing_in_kb_falls_back_to_retrieval():
    agent, rag = _agent({"flat_rag": True}, rows=[])
    response = agent.ask("Vốn điều lệ hiện nay là bao nhiêu?")
    assert rag.calls == ["flat_rag"]
    assert _rules(response)[:2] == ["R3_thuoc_tinh_mot_gia_tri", "R7_mac_dinh_vector"]
    assert response.citations


def test_entity_rule_r6_is_behind_a_flag(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "AGENT_ENTITY_HYBRID", True)
    agent, rag = _agent({"hybrid_rag": True})
    response = agent.ask("Hội đồng Quản trị gồm bao nhiêu thành viên?")
    assert rag.calls == ["hybrid_rag"] and _rules(response)[0] == "R6_co_thuc_the_trong_kb"


def test_article_question_goes_straight_to_hybrid():
    agent, rag = _agent({"hybrid_rag": True})
    agent.ask("Điều 15 của Điều lệ quy định gì?")
    assert rag.calls == ["hybrid_rag"]


def test_no_entity_uses_vector_then_retries_with_graph():
    agent, rag = _agent({"flat_rag": False, "hybrid_rag": True})
    response = agent.ask("Thời gian thử việc tối đa là bao lâu?")
    assert rag.calls == ["flat_rag", "hybrid_rag"]
    assert _rules(response) == ["R7_mac_dinh_vector", "R8_thu_lai_mo_rong", "R2_tra_loi_xong"]


def test_refusal_keeps_the_pipeline_candidates():
    agent, rag = _agent({})
    response = agent.ask("Thời gian thử việc tối đa là bao lâu?")
    assert rag.calls == ["flat_rag", "hybrid_rag"]
    assert response.citations == [] and response.retrieved_chunk_ids == ["c1"]
    assert _rules(response)[-1] == "R9_tu_choi"


def test_without_graph_the_agent_never_asks_for_hybrid():
    agent, rag = _agent({"flat_rag": False}, graph=False)
    agent.ask("Hội đồng Quản trị gồm bao nhiêu thành viên?")
    assert rag.calls == ["flat_rag"]


def test_too_short_question_is_refused_immediately():
    agent, rag = _agent({"flat_rag": True})
    response = agent.ask("?")
    assert rag.calls == [] and _rules(response) == ["R1_cau_hoi_rong"]


def test_rule_table_ends_with_catch_all():
    table = describe()
    assert len(table) == len(RULES) and table[-1]["then"] == "refuse"
