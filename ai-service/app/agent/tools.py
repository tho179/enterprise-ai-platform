"""Tools the agent can call. Each returns an AskResponse-compatible result."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.rag_service import REFUSAL_TEXT, RAGService
from app.schemas import AskResponse, CitationItem

logger = logging.getLogger(__name__)


def _vnd(value: int) -> str:
    return f"{int(value):,}".replace(",", ".") + " đồng"


def _when(row: Dict[str, Any]) -> str:
    """'năm 2026' when only the title's year is known, else dd/mm/yyyy."""
    date = row.get("effective_date")
    if not date:
        return "không rõ ngày hiệu lực"
    year, month, day = date.split("-")
    if row.get("date_source") == "title":
        return f"năm {year}"
    return f"ngày {day}/{month}/{year}"


def _pages(row: Dict[str, Any]) -> str:
    start, end = row.get("page"), row.get("page_end")
    if start is None:
        return "Trang ?"
    return f"Trang {start}" if end in (None, start) else f"Trang {start} → {end}"


class KBAttributeTool:
    """Answer 'what is the current X' from Claim nodes after conflict resolution."""

    name = "kb_attribute"

    def __init__(self, store_factory, source_type: Optional[str] = None):
        self.store_factory = store_factory
        self.source_type = source_type

    def __call__(self, attribute: str, query: str) -> Optional[AskResponse]:
        try:
            rows: List[Dict[str, Any]] = self.store_factory().attribute_values(attribute)
        except Exception as exc:  # the graph is optional
            logger.warning("KB attribute lookup failed: %s", exc)
            return None
        if self.source_type:
            rows = [row for row in rows if row.get("source_type") == self.source_type]
        accepted = [row for row in rows if row.get("status") == "accepted"]
        if not accepted:
            return None
        best = accepted[0]
        history = []
        seen = {best["value"]}
        for row in rows:
            if row.get("status") == "superseded" and row["value"] not in seen:
                seen.add(row["value"])
                history.append(row)
        citations = [
            CitationItem(
                index=index,
                chunk_id=row["chunk_id"],
                score=float(row.get("confidence") or 0.0),
                document_id=row.get("document_id"),
                section_path=list(row.get("section_path") or []),
                pages=_pages(row),
                snippet=row.get("text") or "",
            )
            for index, row in enumerate([best, *history[:2]], start=1)
        ]
        lines = [
            f"{attribute} hiện hành là **{_vnd(best['value'])}**, theo {best['title']} "
            f"({_when(best)}) [1]."
        ]
        if history:
            older = "; ".join(
                f"{_vnd(row['value'])} ({row['title']}, {_when(row)}) [{index}]"
                for index, row in enumerate(history[:2], start=2)
            )
            lines.append(
                f"Các văn bản cũ hơn ghi giá trị khác: {older}. Những giá trị này đã được "
                f"thay thế vì có văn bản hiệu lực mới hơn."
            )
        return AskResponse(
            success=True,
            query=query,
            answer=" ".join(lines),
            citations=citations,
            execution_time_ms=0.0,
            model_used="kb-attribute",
        )


class RetrieveTool:
    """The RAG pipeline: retrieve -> evidence gate -> generate -> verify."""

    name = "retrieve"

    def __init__(self, rag: RAGService):
        self.rag = rag

    def __call__(self, query: str, mode: str, **kwargs) -> AskResponse:
        return self.rag.ask(query=query, retrieval_mode=mode, **kwargs)


def refusal(query: str) -> AskResponse:
    return AskResponse(
        success=True,
        query=query,
        answer=REFUSAL_TEXT,
        citations=[],
        execution_time_ms=0.0,
        model_used="agent-refusal",
    )
