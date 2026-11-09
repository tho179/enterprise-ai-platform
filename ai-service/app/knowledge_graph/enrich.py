"""Give entities a short description and an embedding.

Descriptions come from the source text, so they never invent facts. The
embedding lets a question reach an entity it does not name literally.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Sequence

from .ids import fold

logger = logging.getLogger(__name__)

MAX_DESCRIPTION_CHARS = 240


def describe_entity(name: str, samples: Sequence[str]) -> str:
    """The first source sentence mentioning the entity, else the first sentence."""
    folded_name = fold(name)
    first = ""
    for sample in samples:
        for sentence in re.split(r"(?<=[.;:!?])\s+", re.sub(r"\s+", " ", sample or "").strip()):
            if not sentence:
                continue
            first = first or sentence
            if folded_name and folded_name in fold(sentence):
                return sentence[:MAX_DESCRIPTION_CHARS]
    return first[:MAX_DESCRIPTION_CHARS]


def enrich_entities(store, embedder, batch_size: int = 128) -> int:
    """Fill description/embedding for entities that lack them. Idempotent."""
    total = 0
    while True:
        rows: List[Dict[str, Any]] = store.entities_missing_embedding(limit=batch_size)
        if not rows:
            return total
        descriptions = [
            describe_entity(row["name"], row.get("samples") or []) for row in rows
        ]
        vectors = embedder.embed_documents([
            f"{row['name']}. {description}".strip()
            for row, description in zip(rows, descriptions)
        ])
        store.set_entity_enrichment([
            {"entity_id": row["entity_id"], "description": description, "embedding": vector}
            for row, description, vector in zip(rows, descriptions, vectors)
        ])
        total += len(rows)
        logger.info("Enriched %d entities", total)
