"""Topic-specific answer rules tuned on the current document set.

Every rule here encodes a false positive observed on the sample corpus. They
are kept apart from the generic policy so that a new corpus can run without
them (ANSWER_DOMAIN_RULES=false) and so the evaluation can report results with
and without them. Inputs are always text already passed through `fold_text`.
"""
import re
from typing import List, Optional, Tuple

NO_RULE = object()

_NUMBER = r"(?:\d{1,3}|mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi)"

# Phrases that must appear in the answer window when the question mentions them.
FOCUS_PHRASES = (
    "thoi gio lam viec",
    "thoi gio",
    "thoi han hoat dong",
    "mat khau",
    "lao dong tre em",
    "tre em",
    "tieu chi",
    "nha cung cap",
    "nha cung",
    "quy trinh",
    "hop dong",
    "giao dich",
    "kiem toan",
    "co tuc",
    "co phan",
    "co dong",
    "hoi dong quan tri",
    "dai hoi dong",
    "nguoi lao dong",
    "nhan vien",
    "cho vay",
)
_GENERIC_FOCUS = ("quy trinh", "tieu chi", "nha cung", "thoi gio")


def required_focus(query: str) -> List[str]:
    """Focus phrases the answer window must contain; specific ones win."""
    focus = [phrase for phrase in FOCUS_PHRASES if phrase in query]
    specific = [phrase for phrase in focus if phrase not in _GENERIC_FOCUS]
    return specific or focus


def _near(text: str, anchor: str, pattern: str, window: int) -> bool:
    for match in re.finditer(anchor, text):
        start = max(0, match.start() - window)
        end = min(len(text), match.end() + window)
        if re.search(pattern, text[start:end]):
            return True
    return False


def ratio_rule(q: str, c: str):
    """Shareholder resolutions: the ordinary 50%/65% rule, not the exceptions."""
    if not (("dai hoi dong" in q or "co dong" in q)
            and ("thong qua nghi quyet" in q or "ty le bieu quyet" in q)):
        return NO_RULE
    if "dai hoi dong" in q and "dai hoi dong" not in c:
        return None
    if re.search(
        r"nghi quyet.{0,300}(?:tu 65%|tren 50%|51%|65%).{0,250}tan thanh",
        c,
    ):
        return "ratio"
    return None


def time_rule(q: str, c: str):
    """"Thời hạn hoạt động" is a definition, not any clause containing "thời hạn"."""
    if "thoi han hoat dong" in q or ("thoi han" in q and "hoat dong" in q):
        return "time" if re.search(
            rf"thoi han hoat dong.{{0,120}}(?:vo thoi han|{_NUMBER}\s*(?:nam|thang))",
            c,
        ) else None
    return NO_RULE


def time_anchors(q: str, c: str) -> Optional[List[str]]:
    """Single anchor for topics where the generic anchors pick the wrong clause."""
    for topic in ("hoan", "nhiem ky", "co tuc"):
        if topic in q:
            return [topic] if topic in c else []
    return None


def yesno_rule(q: str, c: str):
    if "kiem toan" in q:
        return "yesno" if re.search(
            r"\b(?:phai|bat buoc)\s+(?:duoc\s+)?kiem toan\b", c
        ) else None
    if "cho vay" in q:
        return "yesno" if _near(
            c, "cho vay", r"quyet dinh|chap thuan", 130
        ) else None
    if "mua lai co phan" in q:
        return "yesno" if (
            re.search(
                r"cong ty.{0,40}mua lai.{0,80}(?:khong qua|duoc|quyet dinh|co the)",
                c,
            )
            or _near(c, "mua lai", r"khong qua|duoc phep|co the|quyet dinh", 100)
        ) else None
    return NO_RULE


def open_rule(q: str, c: str):
    if "quyen han" not in q:
        return NO_RULE
    if "dai hoi dong" in q and "dai hoi dong" not in c:
        return None
    return "default" if re.search(
        r"quyen (?:va nghia vu cua dai hoi dong|va nghia vu sau|han)",
        c,
    ) else None


def citation_limit(q: str, intent: str, limit: int) -> int:
    """Questions whose answer sits in exactly one clause."""
    if "quyen han" in q:
        return 1
    if intent == "time" and ("hoan" in q or "thoi han hoat dong" in q):
        return 1
    return limit
