"""Perception: turn a question into the facts the rules reason about."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from app.embedding_service import fold_text
from app.knowledge_graph.consistency import SINGLE_VALUED
from app.knowledge_graph.extract import LOCAL_ENTITY_TYPES, extract_entities

# Question words that ask for the value of an attribute, not for a procedure.
_VALUE_CUES = ("bao nhieu", "la gi", "hien nay", "hien tai", "hien hanh", "muc", "la bao")
_SHAPES = (
    ("count", r"\b(bao nhieu|may)\b"),
    ("time", r"\b(khi nao|bao lau|thoi han|luc nao|ngay nao)\b"),
    ("yes_no", r"\b(co|duoc)\b.*\bkhong\s*\??$"),
    ("list", r"\b(gom nhung|nhung gi|cac buoc|bao gom|quy trinh)\b"),
)


@dataclass
class Observation:
    question: str
    folded: str
    shape: str = "open"
    article: Optional[str] = None
    attribute: Optional[str] = None
    entities: List[str] = field(default_factory=list)
    content_words: int = 0

    @property
    def has_semantic_entity(self) -> bool:
        return bool(self.entities)

    def as_dict(self) -> dict:
        return {
            "shape": self.shape,
            "article": self.article,
            "attribute": self.attribute,
            "entities": self.entities,
            "content_words": self.content_words,
        }


def perceive(question: str) -> Observation:
    folded = fold_text(question or "")
    observation = Observation(question=question, folded=folded)
    observation.content_words = len(re.findall(r"[a-z0-9]{2,}", folded))

    for shape, pattern in _SHAPES:
        if re.search(pattern, folded):
            observation.shape = shape
            break

    article = re.search(r"\bdieu\s+(\d{1,3})\b", folded)
    if article:
        observation.article = str(int(article.group(1)))
        observation.shape = "article"

    for attribute, spec in SINGLE_VALUED.items():
        if fold_text(spec["phrase"]) in folded and any(cue in folded for cue in _VALUE_CUES):
            observation.attribute = attribute
            break

    observation.entities = [
        entity["name"]
        for entity in extract_entities(question)
        if entity["type"] not in LOCAL_ENTITY_TYPES
    ]
    return observation
