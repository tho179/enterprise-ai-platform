"""Problems that only appear once several sources are merged into one KB.

1. Duplicates   the same document arrives twice (offline PDF corpus and a user
                upload). Detected by word 5-gram shingle overlap.
2. Versions     "Điều lệ 2021", "Điều lệ 2025", "Điều lệ 2026" are versions of
                one document stored as separate files. Grouped by a series key
                (title without the year) and ordered by effective date.
3. Conflicts    sources state different values for an attribute that can have
                only one value at a time ("Vốn điều lệ"). Values are extracted
                as Claims and settled by explicit, ordered rules.

Every function here is pure (no Neo4j); pipeline.maintain() feeds them rows
read with 03_merge_and_resolve.cypher and writes the result back.
"""
from __future__ import annotations

import re
from itertools import combinations
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .ids import digest, fold, fold_keep_length

# ---------------------------------------------------------------- duplicates

# Two bands, as with entity resolution: near-identical text is a duplicate
# and is hidden from retrieval; a large but partial overlap is usually a new
# version or an amendment that copies most of the original, so it is only
# linked (SIMILAR_TO) and both documents stay searchable.
DUPLICATE_THRESHOLD = 0.95
SIMILAR_THRESHOLD = 0.8
SHINGLE = 5


def shingles(text: str, size: int = SHINGLE) -> Set[int]:
    words = re.findall(r"[a-z0-9]+", fold(text))
    if len(words) < size:
        return {hash(" ".join(words))} if words else set()
    return {hash(" ".join(words[i:i + size])) for i in range(len(words) - size + 1)}


def overlap(a: Set[int], b: Set[int]) -> float:
    """Containment of the smaller set: a 30-page copy of a 31-page file is a duplicate."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _keep_rank(doc: Dict[str, Any]) -> Tuple:
    # Prefer the copy users can open in the viewer (upload), then the current,
    # the more trusted and the longer one.
    return (
        doc.get("source_type") == "upload",
        bool(doc.get("is_current", True)),
        float(doc.get("source_trust") or 0),
        len(doc.get("text") or ""),
        doc["doc_id"],
    )


def find_duplicates(
    docs: Sequence[Dict[str, Any]],
    threshold: float = DUPLICATE_THRESHOLD,
    similar: float = SIMILAR_THRESHOLD,
) -> List[Dict[str, Any]]:
    """[{duplicate, keep, overlap, relation}] for document pairs.

    relation is DUPLICATE_OF (overlap >= threshold) or SIMILAR_TO
    (similar <= overlap < threshold).
    """
    sets = {doc["doc_id"]: shingles(doc.get("text") or "") for doc in docs}
    by_id = {doc["doc_id"]: doc for doc in docs}
    pairs: List[Dict[str, Any]] = []
    assigned: Set[str] = set()
    for first, second in combinations(sorted(by_id), 2):
        score = overlap(sets[first], sets[second])
        if score < similar:
            continue
        keep, dup = sorted((by_id[first], by_id[second]), key=_keep_rank, reverse=True)
        relation = "DUPLICATE_OF" if score >= threshold else "SIMILAR_TO"
        if relation == "DUPLICATE_OF":
            if dup["doc_id"] in assigned:
                continue
            assigned.add(dup["doc_id"])
        pairs.append(
            {
                "duplicate": dup["doc_id"],
                "keep": keep["doc_id"],
                "duplicate_title": dup.get("title"),
                "keep_title": keep.get("title"),
                "overlap": round(score, 4),
                "relation": relation,
                "reason": f"shingle_overlap>={threshold if relation == 'DUPLICATE_OF' else similar}",
            }
        )
    return pairs


# ------------------------------------------------------------------ versions

SERIES_SOURCE_TYPES = ("pdf", "web")


def series_key(title: str) -> str:
    """Title without years and punctuation: 'Dieu le cong ty 2025' -> 'dieu le cong ty'."""
    folded = re.sub(r"(?<!\d)(?:19|20)\d{2}(?!\d)", " ", fold(title or ""))
    return " ".join(re.findall(r"[a-z0-9]+", folded))


def find_series(docs: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """NEW_VERSION_OF links between consecutive dated members of one series."""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for doc in docs:
        if doc.get("source_type") not in SERIES_SOURCE_TYPES or not doc.get("effective_date"):
            continue
        if doc.get("superseded_reason") not in (None, "series"):
            continue  # already historical for another reason
        if not re.search(r"(?:19|20)\d{2}", doc.get("title") or ""):
            continue  # only titles that carry their own year form a series
        groups.setdefault(series_key(doc.get("title", "")), []).append(doc)

    links: List[Dict[str, Any]] = []
    for key, members in groups.items():
        if len(members) < 2:
            continue
        members = sorted(members, key=lambda d: (d["effective_date"], d["doc_id"]))
        for older, newer in zip(members, members[1:]):
            links.append(
                {
                    "series": key,
                    "old": older["doc_id"],
                    "new": newer["doc_id"],
                    "old_title": older.get("title"),
                    "new_title": newer.get("title"),
                }
            )
    return links


# ----------------------------------------------------------------- conflicts

# Attributes that hold exactly one value at a time. Each entry: canonical
# entity name, accent-free trigger phrases, and the value kind.
SINGLE_VALUED = {
    "Vốn điều lệ": {"phrase": "vốn điều lệ", "kind": "money"},
    "Mệnh giá cổ phần": {"phrase": "mệnh giá", "kind": "money_small"},
}


_fold_same_length = fold_keep_length

_MONEY_BIG = re.compile(
    r"(\d{1,3}(?:[.,]\d{3}){3,})\s*(?:\([^)]{0,200}\)\s*)?(?:đồng|đông|dong|VNĐ|VND)",
    re.IGNORECASE,
)
_MONEY_SMALL = re.compile(r"(\d{1,3}(?:[.,]\d{3})+|\d+)\s*(?:\([^)]{0,80}\)\s*)?(?:đồng|đông|dong|VNĐ|VND)", re.IGNORECASE)
_SHARES = re.compile(r"chia\s+thành\s*:?\s*(\d{1,3}(?:[.,]\d{3})+)", re.IGNORECASE)
_PAR = re.compile(r"mệnh\s+giá\s*(?:là\s*)?:?\s*(\d{1,3}(?:[.,]\d{3})+)", re.IGNORECASE)
_SENTENCE = re.compile(r"(?<=[;!?])\s+|(?<=\.)\s+(?=[A-ZĐÀ-Ỹ_\-\d])|\n+")


def _number(raw: str) -> int:
    return int(re.sub(r"[.,]", "", raw))


def _value_after(sentence: str, start: int, kind: str) -> Optional[int]:
    pattern = _MONEY_BIG if kind == "money" else _MONEY_SMALL
    match = pattern.search(sentence, start)
    if not match or match.start() - start > 160:
        return None
    return _number(match.group(1))


def extract_claims(chunk: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Claims stated by one chunk, with plausibility flags."""
    text = chunk.get("text") or ""
    claims: List[Dict[str, Any]] = []
    shares = _SHARES.search(text)
    par = _PAR.search(text)
    for sentence in _SENTENCE.split(text):
        folded_sentence = _fold_same_length(sentence)
        for attribute, spec in SINGLE_VALUED.items():
            # Match accent-free so OCR forms ("Vôn Điều Lệ") still count.
            position = folded_sentence.find(fold(spec["phrase"]))
            if position < 0:
                continue
            value = _value_after(sentence, position, spec["kind"])
            if value is None:
                continue
            flags: List[str] = []
            if attribute == "Vốn điều lệ" and shares and par:
                implied = _number(shares.group(1)) * _number(par.group(1))
                if implied and abs(implied - value) / value > 0.001:
                    flags.append("lech_so_co_phan_x_menh_gia")
            exact = spec["phrase"] in sentence.casefold()
            if not exact:
                flags.append("khop_khong_dau")
            confidence = (0.9 if exact else 0.6) * float(chunk.get("source_trust") or 0.5)
            if "lech_so_co_phan_x_menh_gia" in flags:
                confidence *= 0.5
            claims.append(
                {
                    "claim_id": "clm-" + digest(chunk["chunk_id"], attribute, str(value)),
                    "attribute": attribute,
                    "value": value,
                    "unit": "VND",
                    "text": sentence.strip()[:300],
                    "confidence": round(confidence, 3),
                    "flags": flags,
                    "chunk_id": chunk["chunk_id"],
                    "doc_id": chunk.get("doc_id"),
                    "title": chunk.get("title"),
                    "page": chunk.get("page"),
                    "source_type": chunk.get("source_type"),
                    "source_trust": chunk.get("source_trust"),
                    "is_current": chunk.get("is_current", True),
                    "effective_date": chunk.get("effective_date"),
                }
            )
    # One claim per (chunk, attribute, value).
    unique = {claim["claim_id"]: claim for claim in claims}
    return list(unique.values())


def _priority(claim: Dict[str, Any]) -> Tuple:
    """Ordered resolution rules, most important first."""
    return (
        bool(claim.get("is_current", True)),     # R1 current document beats a superseded one
        claim.get("effective_date") or "",        # R2 newer effective date wins
        float(claim.get("source_trust") or 0),    # R3 official source beats web summary
        "lech_so_co_phan_x_menh_gia" not in (claim.get("flags") or []),  # R4 plausible value
        float(claim.get("confidence") or 0),      # R5 extraction confidence
    )


def _reason(winner: Dict[str, Any], loser: Dict[str, Any]) -> str:
    if winner.get("is_current", True) and not loser.get("is_current", True):
        return "R1_ban_hien_hanh"
    if (winner.get("effective_date") or "") > (loser.get("effective_date") or ""):
        return "R2_hieu_luc_moi_hon"
    if float(winner.get("source_trust") or 0) > float(loser.get("source_trust") or 0):
        return "R3_nguon_tin_cay_hon"
    flag = "lech_so_co_phan_x_menh_gia"
    if flag not in (winner.get("flags") or []) and flag in (loser.get("flags") or []):
        return "R4_gia_tri_hop_ly_hon"
    return ""


def resolve_conflicts(claims: Iterable[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Set claim['status'] and return (claims, conflict edges).

    status: accepted     the value the KB answers with (or agrees with it)
            superseded   a different value that lost under rules R1-R4
            unresolved   no rule separates it from the winner (needs a human)
    """
    claims = list(claims)
    conflicts: List[Dict[str, Any]] = []
    by_attribute: Dict[str, List[Dict[str, Any]]] = {}
    for claim in claims:
        by_attribute.setdefault(claim["attribute"], []).append(claim)

    for group in by_attribute.values():
        ranked = sorted(group, key=_priority, reverse=True)
        winner = ranked[0]
        for claim in ranked:
            if claim["value"] == winner["value"]:
                claim["status"] = "accepted"
                continue
            reason = _reason(winner, claim)
            claim["status"] = "superseded" if reason else "unresolved"
            conflicts.append(
                {
                    "loser": claim["claim_id"],
                    "winner": winner["claim_id"],
                    "resolution": claim["status"],
                    "reason": reason or "khong_phan_dinh_duoc",
                }
            )
        if any(claim["status"] == "unresolved" for claim in group):
            winner["status"] = "unresolved"
    return claims, conflicts
