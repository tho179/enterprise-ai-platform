"""Rule-based question-answering agent on top of the RAG pipeline.

perceive (perception.py) -> match rules (rules.py) -> act with a tool
(tools.py) -> observe -> respond or re-plan. The loop lives in agent.py.
"""
from .agent import RuleBasedAgent

__all__ = ["RuleBasedAgent"]
