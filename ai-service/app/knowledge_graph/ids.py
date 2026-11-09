"""Content-addressed IDs for the knowledge-graph prototype.

IDs are derived from content, not from insertion order. That makes ingestion
idempotent and lets KB1/KB2 share the same Document/Chunk/Entity nodes when
they contain the same source.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata


def fold(text: str) -> str:
    """Lower-case, strip Vietnamese accents and collapse whitespace."""
    text = unicodedata.normalize("NFD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", text).strip().casefold()


def sha1_text(text: str) -> str:
    return hashlib.sha1((text or "").encode("utf-8")).hexdigest()


def digest(*parts: str) -> str:
    raw = "\x1f".join(parts).encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:16]


def document_id(content_hash: str, title: str) -> str:
    return "doc-" + digest(content_hash, fold(title))


def chunk_id(doc_id: str, index: int, content: str) -> str:
    return "chk-" + digest(doc_id, str(index), sha1_text(content))


def entity_id(name: str, kind: str) -> str:
    return "ent-" + digest(fold(name), kind)
