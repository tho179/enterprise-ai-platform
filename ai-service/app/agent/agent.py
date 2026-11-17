"""The agent loop: perceive -> match a rule -> act -> observe, at most MAX_STEPS."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from app.config import settings
from app.knowledge_graph.service import _graph_enabled, get_store
from app.rag_service import RAGService
from app.schemas import AskResponse

from .perception import perceive
from .rules import AgentState, match
from .tools import KBAttributeTool, RetrieveTool, refusal

logger = logging.getLogger(__name__)

MAX_STEPS = 4


class RuleBasedAgent:
    """Drop-in replacement for RAGService.ask that chooses its own strategy.

    The caller's retrieval_mode is ignored: choosing it is the agent's job.
    Every decision is recorded in AskResponse.agent_trace.
    """

    def __init__(
        self,
        rag: Optional[RAGService] = None,
        store_factory=get_store,
        graph_available=None,
        source_type: Optional[str] = None,
    ):
        self.rag = rag or RAGService()
        self.retrieve = RetrieveTool(self.rag)
        self.kb_attribute = KBAttributeTool(store_factory, source_type=source_type)
        self._graph_available = graph_available

    @property
    def retriever(self):  # used by callers that share the cached retriever
        return self.rag.retriever

    def ask(self, query: str, retrieval_mode: Optional[str] = None, **kwargs) -> AskResponse:
        started = time.time()
        observation = perceive(query)
        graph = self._graph_available if self._graph_available is not None else _graph_enabled()
        state = AgentState(graph_available=graph)
        trace: List[Dict[str, Any]] = [{"step": 0, "perception": observation.as_dict()}]
        response: Optional[AskResponse] = None

        while state.steps < MAX_STEPS:
            state.steps += 1
            rule = match(observation, state)
            step_started = time.time()
            entry: Dict[str, Any] = {"step": state.steps, "rule": rule.name, "action": rule.action}

            if rule.action == "respond":
                trace.append(entry)
                break
            if rule.action == "refuse":
                # Keep a gate refusal from the pipeline: it carries the
                # retrieved candidates the benchmark scores.
                if response is None or response.citations:
                    response = refusal(query)
                trace.append(entry)
                break
            if rule.action == "kb_attribute":
                result = self.kb_attribute(observation.attribute, query)
                state.attribute_found = result is not None
                entry["result"] = "found" if result else "not_found"
                if result is not None:
                    response = result
            elif rule.action.startswith("retrieve:"):
                mode = rule.action.split(":", 1)[1]
                state.tried.append(mode)
                response = self.retrieve(query, mode, **kwargs)
                state.last_answered = bool(response.citations)
                entry["result"] = "answered" if state.last_answered else "gate_refused"
                entry["citations"] = len(response.citations)
            state.last_action = rule.action
            entry["ms"] = round((time.time() - step_started) * 1000, 1)
            trace.append(entry)

        if response is None:
            response = refusal(query)
        response.execution_time_ms = round((time.time() - started) * 1000, 2)
        response.agent_trace = trace
        logger.info("Agent: %s", [(item.get("rule"), item.get("result")) for item in trace[1:]])
        return response


def agent_enabled() -> bool:
    return settings.AGENT_ENABLED
