"""Fuzzy entity resolution: decide when two entity names mean the same thing.

Rule extraction already maps known aliases ("HĐQT", "Board of Directors") to
one canonical entity. What it cannot catch are free-text headings that differ
slightly between sources or because of OCR, e.g.
  "Quyền và nghĩa vụ của cổ đông" vs "Quyền, nghĩa vụ của cổ đông".

Similarity is a number in [0, 1]; the decision uses a fuzzy membership
function instead of one hard threshold:

    μ_same(s) = 0                     if s <= LOW
              = (s - LOW)/(HIGH-LOW)  if LOW < s < HIGH
              = 1                     if s >= HIGH

  μ = 1      -> SAME_AS           (merged for retrieval)
  0 < μ < 1  -> POSSIBLY_SAME_AS  (kept apart, queued for human review)
  μ = 0      -> different entities

Two crisp guards run first, because similar strings are not always the same
thing: different numbers ("Nghị định 155/2020" vs "156/2020") never match,
and numbered types (articles, dates) are never fuzzy-matched.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from itertools import combinations
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from .ids import fold

LOW = 0.80
HIGH = 0.92
RESOLVABLE_TYPES = ("tieu_de", "chu_de", "chuc_danh", "van_ban")
_STOP = {"va", "cua", "cac", "ve", "doi", "voi", "trong", "the", "and", "of"}
_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(folded: str) -> Set[str]:
    return {token for token in _TOKEN.findall(folded) if token not in _STOP}


def _numbers(folded: str) -> Set[str]:
    return {str(int(number)) for number in re.findall(r"\d+", folded)}


def similarity(a: str, b: str) -> float:
    """max(character ratio, content-word Jaccard) on accent-free names."""
    fa, fb = fold(a), fold(b)
    if fa == fb:
        return 1.0
    if _numbers(fa) != _numbers(fb):
        return 0.0
    ratio = SequenceMatcher(None, fa, fb).ratio()
    ta, tb = _tokens(fa), _tokens(fb)
    jaccard = len(ta & tb) / len(ta | tb) if ta and tb else 0.0
    return round(max(ratio, jaccard), 4)


POLARITY = {"chua", "khong", "da", "not", "non", "no", "un"}


def polarity_differs(a: str, b: str) -> bool:
    """True when the names differ by a negation/aspect word."""
    return bool((_tokens(fold(a)) ^ _tokens(fold(b))) & POLARITY)


def membership(score: float, low: float = LOW, high: float = HIGH) -> float:
    if score <= low:
        return 0.0
    if score >= high:
        return 1.0
    return round((score - low) / (high - low), 4)


def decide(score: float) -> Optional[str]:
    mu = membership(score)
    if mu >= 1.0:
        return "SAME_AS"
    if mu > 0.0:
        return "POSSIBLY_SAME_AS"
    return None


def resolve_pairs(
    entities: Iterable[Dict[str, Any]],
    manual: Optional[Dict[Tuple[str, str], str]] = None,
) -> List[Dict[str, Any]]:
    """Candidate pairs of the same type with their decision.

    `manual` holds reviewer decisions keyed by (entity_id, entity_id); those
    pairs are skipped so a later run never overrides a human.
    """
    manual = manual or {}
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for entity in entities:
        if entity.get("type") in RESOLVABLE_TYPES:
            by_type.setdefault(entity["type"], []).append(entity)

    pairs: List[Dict[str, Any]] = []
    for group in by_type.values():
        for first, second in combinations(sorted(group, key=lambda e: e["entity_id"]), 2):
            key = (first["entity_id"], second["entity_id"])
            if key in manual or key[::-1] in manual:
                continue
            score = similarity(first["name"], second["name"])
            relation = decide(score)
            guard = None
            if relation == "SAME_AS" and polarity_differs(first["name"], second["name"]):
                # "đã xác định" vs "chưa xác định": one word apart, opposite meaning.
                relation, guard = "POSSIBLY_SAME_AS", "phu_dinh"
            if relation:
                pairs.append(
                    {
                        "a": first["entity_id"],
                        "b": second["entity_id"],
                        "a_name": first["name"],
                        "b_name": second["name"],
                        "score": score,
                        "membership": membership(score),
                        "relation": relation,
                        "method": "fuzzy_lexical",
                        "guard": guard,
                    }
                )
    return sorted(pairs, key=lambda pair: pair["score"], reverse=True)
