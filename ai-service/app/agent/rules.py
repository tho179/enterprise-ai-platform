"""The agent's policy: an ordered table of production rules.

Each rule is IF <condition on observation and state> THEN <action>. The first
rule whose condition holds fires (priority = position in RULES). Rules are
data, so the table can be printed for the report and tested one by one.

Actions
  refuse                  answer with the refusal text, no citation
  kb_attribute            read the resolved value from the KB (Claim nodes)
  retrieve:<mode>         run the RAG pipeline with flat_rag / hybrid_rag
  respond                 return the last observation as the answer
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from app.config import settings

from .perception import Observation


@dataclass
class AgentState:
    steps: int = 0
    tried: List[str] = field(default_factory=list)
    last_action: Optional[str] = None
    last_answered: Optional[bool] = None   # None: nothing tried yet
    attribute_found: Optional[bool] = None
    graph_available: bool = True


@dataclass(frozen=True)
class Rule:
    name: str
    description: str
    condition: Callable[[Observation, AgentState], bool]
    action: str


def _retrieved_and_answered(obs: Observation, state: AgentState) -> bool:
    return bool(state.last_action and state.last_action.startswith("retrieve:") and state.last_answered)


RULES: List[Rule] = [
    Rule(
        "R1_cau_hoi_rong",
        "Câu hỏi quá ngắn để tìm kiếm (dưới 2 từ có nghĩa)",
        lambda o, s: o.content_words < 2,
        "refuse",
    ),
    Rule(
        "R2_tra_loi_xong",
        "Lần truy xuất trước đã có câu trả lời qua cổng bằng chứng",
        _retrieved_and_answered,
        "respond",
    ),
    Rule(
        "R3_thuoc_tinh_mot_gia_tri",
        "Hỏi giá trị của thuộc tính chỉ có một giá trị (vốn điều lệ, mệnh giá): "
        "đọc giá trị đã giải quyết mâu thuẫn trong KB",
        lambda o, s: bool(o.attribute) and s.graph_available and s.attribute_found is None,
        "kb_attribute",
    ),
    Rule(
        "R4_thuoc_tinh_da_co",
        "KB đã có giá trị được chấp nhận cho thuộc tính",
        lambda o, s: s.last_action == "kb_attribute" and bool(s.attribute_found),
        "respond",
    ),
    Rule(
        "R5_dan_chieu_dieu_khoan",
        "Câu hỏi nêu số điều (Điều N): cần đồ thị để theo cạnh REFERENCES",
        lambda o, s: bool(o.article) and s.graph_available and "hybrid_rag" not in s.tried,
        "retrieve:hybrid_rag",
    ),
    Rule(
        "R6_co_thuc_the_trong_kb",
        "Câu hỏi nhắc thực thể có trong KB (chức danh, chủ đề, văn bản): dùng truy xuất lai. "
        "Tắt mặc định (AGENT_ENTITY_HYBRID) vì thực nghiệm bandit cho thấy vector tốt hơn ở ngữ cảnh này",
        lambda o, s: settings.AGENT_ENTITY_HYBRID and o.has_semantic_entity
        and s.graph_available and "hybrid_rag" not in s.tried,
        "retrieve:hybrid_rag",
    ),
    Rule(
        "R7_mac_dinh_vector",
        "Không có thực thể nào: vector search là đủ, bỏ chi phí truy vấn đồ thị",
        lambda o, s: not s.tried,
        "retrieve:flat_rag",
    ),
    Rule(
        "R8_thu_lai_mo_rong",
        "Vector search bị cổng bằng chứng từ chối: thử lại với truy xuất lai",
        lambda o, s: s.last_answered is False and "hybrid_rag" not in s.tried and s.graph_available,
        "retrieve:hybrid_rag",
    ),
    Rule(
        "R9_tu_choi",
        "Đã thử hết công cụ mà không đủ căn cứ",
        lambda o, s: True,
        "refuse",
    ),
]


def match(observation: Observation, state: AgentState) -> Rule:
    for rule in RULES:
        if rule.condition(observation, state):
            return rule
    raise RuntimeError("RULES must end with a catch-all rule")


def describe() -> List[Dict[str, Any]]:
    """The rule table, for documentation and the /agent/rules endpoint."""
    return [
        {"priority": index, "name": rule.name, "if": rule.description, "then": rule.action}
        for index, rule in enumerate(RULES, start=1)
    ]
