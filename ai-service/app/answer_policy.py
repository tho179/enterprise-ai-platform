"""Answer policy: decide which retrieved passages may support an answer.

Three layers, from generic to corpus-specific:
1. `_answer_shape`: the passage must contain the *kind* of information asked
   for (a number for "bao nhiêu", a duration for "bao lâu", ...).
2. `select_evidence`: cross-encoder scoring of short answer windows and the
   refuse-or-answer gate.
3. `app.answer_rules`: optional topic rules tuned on the current corpus. They
   only tighten the decision and can be switched off with
   ANSWER_DOMAIN_RULES=false.
"""
import logging
import math
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from app import answer_rules as rules
from app.config import settings
from app.embedding_service import fold_text

logger = logging.getLogger(__name__)

# Từ chức năng khi chọn câu trả lời trích xuất; giữ nguyên từ chuyên môn.
_STOPWORDS = {
    "la", "cua", "co", "va", "duoc", "bao", "nhieu", "gi", "nao", "the", "nhu",
    "khi", "cho", "trong", "mot", "cac", "nhung", "nay", "do", "de", "voi",
    "hay", "hoac", "thi", "ma", "o", "ra", "vao", "len", "xuong", "roi", "da",
    "dang", "se", "toi", "ban", "minh", "tren", "duoi", "tu", "den", "ve",
    "tai", "boi", "vi", "nen", "cung", "chi", "con", "ai", "lam", "sao", "phai",
    "khong", "bi", "moi", "vay", "nhi", "rat", "qua", "hon", "nua", "day", "kia",
    "ay", "no", "ho", "chung",
}


def _content_terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[0-9a-z]+", fold_text(text))
        if len(token) > 1 and token not in _STOPWORDS
    }


def _content_tokens(text: str) -> List[str]:
    return [
        token
        for token in re.findall(r"[0-9a-z]+", fold_text(text))
        if len(token) > 1 and token not in _STOPWORDS
    ]


def _bigrams(text: str) -> set[str]:
    tokens = _content_tokens(text)
    return {
        f"{left} {right}"
        for left, right in zip(tokens, tokens[1:])
    }


# Các cụm danh từ nghiệp vụ thường gặp. Dùng để kiểm tra câu trả lời có đúng
# *loại thông tin* người dùng hỏi hay không (số lượng, thời hạn, tỷ lệ...).
_ENTITY_TERMS = (
    "co dong",
    "co phan",
    "thanh vien",
    "hoi dong quan tri",
    "uy ban kiem toan",
    "tong giam doc",
    "hop dong",
    "giao dich",
    "co tuc",
    "nguoi lao dong",
    "nhan vien",
    "tai san",
    "von dieu le",
)

_NUMBER = r"(?:\d{1,3}|mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi)"
_TIME_UNIT = r"(?:ngay|thang|nam|gio|phut|tuan)"
_ROLE_TERMS = (
    "tong giam doc",
    "hoi dong quan tri",
    "chu tich",
    "nguoi dai dien",
    "dai hoi dong",
    "giam doc",
    "ke toan truong",
)


def _near(text: str, anchor: str, pattern: str, window: int = 160) -> bool:
    """True nếu `pattern` xuất hiện trong vùng lân cận của `anchor`."""
    for match in re.finditer(anchor, text):
        start = max(0, match.start() - window)
        end = min(len(text), match.end() + window)
        if re.search(pattern, text[start:end]):
            return True
    return False


def _counted_noun(q: str) -> List[str]:
    """"có bao nhiêu chi nhánh" -> ["chi nhanh"] for nouns outside the lexicon."""
    match = re.search(r"bao nhieu ((?:[a-z0-9]+ ?){1,2})", q)
    if not match:
        return []
    words = match.group(1).split()
    while words and words[-1] in _STOPWORDS:
        words.pop()
    return [" ".join(words)] if words else []


def _answer_shape(query: str, content: str) -> Optional[str]:
    """
    Xác định câu trả lời có đúng dạng thông tin câu hỏi cần không.

    Đây là lớp chặn false-positive rẻ tiền nhưng hiệu quả với văn bản pháp lý:
    câu hỏi "bao nhiêu cổ đông" không được trả lời bằng một đoạn chỉ nói về
    quyền của cổ đông, dù đoạn đó có điểm rerank cao.
    """
    q = fold_text(query)
    c = fold_text(content)
    if not q or not c:
        return None

    # "Cuộc họp lần thứ ba" phải lấy đúng đoạn nói về lần thứ ba, không phải
    # đoạn lần thứ hai đứng ngay trước.
    meeting = re.search(r"lan thu (nhat|hai|ba|bon|nam|sau|bay|tam|chin|muoi)", q)
    if meeting:
        ordinal = meeting.group(1)
        return "meeting" if re.search(rf"\blan thu {ordinal}\b", c) else None

    article = re.search(r"\bdieu\s+(\d{1,3})\b", q)
    if article:
        return "article" if re.search(rf"\bdieu\s+{article.group(1)}\b", c) else None

    time_asked = bool(
        re.search(r"bao lau|khi nao|thoi han|thoi gian|toi da", q)
        or re.search(r"bao nhieu (?:ngay|thang|nam|gio|phut|tuan)", q)
    )
    ratio_asked = bool(re.search(r"ty le|phan tram|%", q))
    value_asked = bool(re.search(r"gia tri.*bao nhieu|bao nhieu tien|so tien", q))
    count_asked = "bao nhieu" in q and not time_asked and not ratio_asked

    if ratio_asked or value_asked:
        if settings.ANSWER_DOMAIN_RULES:
            verdict = rules.ratio_rule(q, c)
            if verdict is not rules.NO_RULE:
                return verdict

        anchors = [
            term for term in (
                "ty le", "phan tram", "gia tri", "hop dong", "giao dich",
                "co phan", "co dong", "phieu",
            )
            if term in q and term in c
        ]
        for anchor in anchors:
            if _near(c, anchor, r"%|phan tram", 180):
                return "ratio"
        # Đoạn đúng có thể chỉ nêu "65% ... biểu quyết" mà không lặp lại chữ
        # "tỷ lệ"; vẫn nhận nếu con số % nằm cạnh hành động liên quan.
        for key in ("bieu quyet", "nghi quyet", "co phan", "co dong", "phieu"):
            if key in q and key in c and _near(c, key, r"%", 220):
                return "ratio"
        return None

    if count_asked:
        if "cuoc hop" in q or "hop" in q:
            if re.search(r"(?:it nhat|moi quy|moi nam|hang nam).{0,50}(?:hop|cuoc hop|lan)", c) or re.search(r"(?:hop|cuoc hop).{0,50}(?:it nhat|moi quy|moi nam|lan)", c):
                return "count"
        entities = [term for term in _ENTITY_TERMS if term in q] or _counted_noun(q)
        if not entities:
            return None
        entity_pattern = "|".join(re.escape(term) for term in entities)
        # Chỉ chấp nhận số đứng ngay trước danh từ ("có từ 03 đến 11 thành viên")
        # hoặc "số lượng ... là 05". Cách này loại được "10% tổng số cổ phần".
        direct = re.compile(
            rf"(?<![\d/]){_NUMBER}(?:\s+den\s+{_NUMBER})?\s+"
            rf"(?:nguoi\s+)?(?:{entity_pattern})\b"
        )
        explicit = re.compile(
            rf"(?:so luong|tong so).{{0,35}}(?:{entity_pattern})"
            rf".{{0,20}}(?:la|gom|co)?\s*{_NUMBER}\b"
        )
        if direct.search(c) or explicit.search(c):
            return "count"
        return None

    if time_asked:
        anchors = None
        if settings.ANSWER_DOMAIN_RULES:
            verdict = rules.time_rule(q, c)
            if verdict is not rules.NO_RULE:
                return verdict
            anchors = rules.time_anchors(q, c)
        if anchors is None:
            anchors = [
                term for term in (
                    "thoi han", "thoi gian", "tra", "hieu luc", "to chuc",
                    "thong bao", "hop", "nhiem ky", "hoan",
                )
                if term in q and term in c
            ]
            if not anchors and not settings.ANSWER_DOMAIN_RULES:
                anchors = sorted(
                    term for term in _content_terms(q) & _content_terms(c)
                    if len(term) >= 4
                )
        for anchor in anchors:
            # Nhiệm kỳ phải đi với đơn vị năm/tháng, không phải "bảy ngày" của
            # cuộc họp bầu Chủ tịch.
            unit = r"(?:nam|thang)" if anchor == "nhiem ky" else _TIME_UNIT
            if _near(c, anchor, rf"\b{_NUMBER}\s*{unit}\b|khong qua|cham nhat|vo thoi han", 200):
                return "time"
            if "khi nao" in q and _near(c, anchor, r"\bkhi\b", 200):
                return "time"
        return None

    yes_no = bool(
        re.search(r"\bco\b.*\bkhong\b", q)
        or re.search(r"\bco phai\b|\bbat buoc\b|\bco the\b|\bduoc phep\b", q)
    )
    if yes_no:
        if settings.ANSWER_DOMAIN_RULES:
            verdict = rules.yesno_rule(q, c)
            if verdict is not rules.NO_RULE:
                return verdict
        keys = [term for term in _ENTITY_TERMS if term in q] or [
            bigram for bigram in sorted(_bigrams(q)) if bigram in c
        ]
        if keys:
            return "yesno" if _near(
                c, re.escape(keys[0]),
                r"\bphai\b|\bduoc\b|\bco the\b|\bkhong duoc\b|\bkhong the\b|\bchi duoc\b",
                120,
            ) else None
        return None

    if "ai" in re.findall(r"[a-z]+", q) or "nguoi nao" in q:
        if "ky" in q:
            actions = r"ky ket|ky hop dong|\bky\b"
        elif "quyet dinh" in q:
            actions = r"quyet dinh|phe duyet|chap thuan"
        elif "bo nhiem" in q:
            actions = r"bo nhiem|mien nhiem|bai nhiem"
        else:
            actions = r"quyet dinh|dai dien|dieu hanh|bo nhiem"
        for role in _ROLE_TERMS:
            if role in c and _near(c, role, actions, 150):
                return "who"
        return None

    # Câu hỏi mở chỉ cần độ phủ từ khóa đủ cao; không hạ ngưỡng xuống mức biến
    # đoạn nhiễu thành câu trả lời.
    if settings.ANSWER_DOMAIN_RULES:
        verdict = rules.open_rule(q, c)
        if verdict is not rules.NO_RULE:
            return verdict

    query_terms = _content_terms(q)
    content_terms = _content_terms(c)
    if not query_terms:
        return None
    # Một từ khóa dài (>= 4 ký tự) phải thực sự xuất hiện; tránh trường hợp
    # "pizza hải sản" khớp nhầm nhãn "Hải Sản" trong bảng giá.
    if not any(len(term) >= 4 and term in content_terms for term in query_terms):
        return None
    overlap = len(query_terms & content_terms) / len(query_terms)
    return "default" if overlap >= 0.3 else None


def _coverage(query: str, text: str) -> float:
    query_terms = _content_terms(query)
    if not query_terms:
        return 0.0
    return len(query_terms & _content_terms(text)) / len(query_terms)


def _term_weights(query: str, hits: List[Dict[str, Any]]) -> Dict[str, float]:
    """IDF thô trên tập ứng viên: từ hiếm như "mật khẩu", "trẻ em" có trọng số cao."""
    terms = _content_terms(query)
    if not terms or not hits:
        return {term: 1.0 for term in terms}
    total = len(hits)
    df = {
        term: sum(1 for hit in hits if term in _content_terms(hit.get("content", "")))
        for term in terms
    }
    return {
        term: math.log((total + 1) / (df[term] + 1)) + 1.0
        for term in terms
    }


def _weighted_coverage(query: str, text: str, weights: Dict[str, float]) -> float:
    query_terms = _content_terms(query)
    if not query_terms:
        return 0.0
    text_terms = _content_terms(text)
    total = sum(weights.get(term, 1.0) for term in query_terms)
    matched = sum(
        weights.get(term, 1.0) for term in query_terms if term in text_terms
    )
    return matched / total if total else 0.0


def _bigram_weights(
    query: str, hits: List[Dict[str, Any]]
) -> Tuple[Dict[str, float], Dict[str, int]]:
    query_bigrams = _bigrams(query)
    if not query_bigrams or not hits:
        return {bigram: 1.0 for bigram in query_bigrams}, {
            bigram: 0 for bigram in query_bigrams
        }
    total = len(hits)
    df = {
        bigram: sum(
            1 for hit in hits
            if bigram in _bigrams(hit.get("content", ""))
        )
        for bigram in query_bigrams
    }
    weights = {
        bigram: math.log((total + 1) / (df[bigram] + 1)) + 1.0
        for bigram in query_bigrams
    }
    return weights, df


def _weighted_bigram_coverage(
    query: str, text: str, weights: Dict[str, float]
) -> float:
    query_bigrams = _bigrams(query)
    if not query_bigrams:
        return 0.0
    text_bigrams = _bigrams(text)
    total = sum(weights.get(bigram, 1.0) for bigram in query_bigrams)
    matched = sum(
        weights.get(bigram, 1.0)
        for bigram in query_bigrams
        if bigram in text_bigrams
    )
    return matched / total if total else 0.0


def _answer_windows(content: str, max_chars: int = 800):
    """
    Sinh các cửa sổ 1-4 câu để cross-encoder chấm đúng câu trả lời.

    Chunk 1.400 ký tự thường trộn nhiều quy định; chấm cả chunk làm câu đúng bị
    pha loãng bởi OCR và các đoạn không liên quan.
    """
    normalized = re.sub(r"\s+", " ", content).strip()
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?;:])\s+", normalized)
        if sentence.strip()
    ]
    if not sentences:
        yield content
        return

    seen = set()
    for start in range(len(sentences)):
        parts = []
        for end in range(start, min(len(sentences), start + 4)):
            parts.append(sentences[end])
            window = " ".join(parts).strip()
            if len(window) > max_chars:
                break
            key = fold_text(window)
            if key in seen:
                continue
            seen.add(key)
            yield window


LIST_MARKERS = ("gom nhung", "tieu chi", "cac buoc", "bao gom", "quy trinh")


def _list_windows(query: str, content: str, max_chars: int = 900):
    """Cửa sổ bắt đầu tại chỗ nêu chủ đề để câu trả lời không chỉ trúng mục cuối."""
    folded_query = fold_text(query)
    if not any(marker in folded_query for marker in LIST_MARKERS):
        return

    normalized = re.sub(
        r"\s+", " ", unicodedata.normalize("NFC", content)
    ).strip()
    folded = fold_text(normalized)
    if len(folded) != len(normalized):  # offsets are only valid 1:1
        return

    tokens = _content_tokens(query)
    positions = [
        folded.find(f"{left} {right}")
        for left, right in zip(tokens, tokens[1:])
    ]
    positions = [position for position in positions if position >= 0]
    if not positions:
        return

    start = min(positions)
    sentence_start = normalized.rfind(". ", 0, start)
    if sentence_start >= 0 and start - sentence_start <= 200:
        start = sentence_start + 2
    elif start <= 200:
        start = 0
    yield normalized[start:start + max_chars]


def select_evidence(
    query: str,
    hits: List[Dict[str, Any]],
    top_k: int,
    reranker: Any,
    use_reranker: bool = True,
) -> List[Dict[str, Any]]:
    """Return the hits allowed to support an answer; empty means refuse.

    Each returned hit carries `answer_window`, the sentences that were scored.
    """
    query_terms = _content_terms(query)
    if hits and query_terms:
        # Nếu từ dài nhất của câu hỏi không xuất hiện ở bất kỳ ứng viên nào
        # (ví dụ "pizza"), câu hỏi gần như chắc chắn ngoài phạm vi tài liệu.
        corpus_terms = set().union(
            *(_content_terms(hit.get("content", "")) for hit in hits)
        )
        longest = max(len(term) for term in query_terms)
        if longest >= 4 and not any(
            term in corpus_terms
            for term in query_terms
            if len(term) == longest
        ):
            return []

    weights = _term_weights(query, hits)
    bigram_weights, _bigram_df = _bigram_weights(query, hits)
    folded_query = fold_text(query)
    focus = rules.required_focus(folded_query) if settings.ANSWER_DOMAIN_RULES else []

    candidates: List[Tuple[Any, ...]] = []
    for hit in hits:
        hit_score = float(hit.get("score", 0.0))
        if hit_score < 0.25 and not hit.get("article_match"):
            continue
        window_specs = [
            (window, False) for window in _answer_windows(hit.get("content", ""))
        ]
        window_specs.extend(
            (window, True) for window in _list_windows(query, hit.get("content", ""))
        )
        windows = []
        for window, is_list in window_specs:
            shape = _answer_shape(query, window)
            if not shape:
                continue
            if focus:
                window_folded = fold_text(window)
                if not any(phrase in window_folded for phrase in focus):
                    continue
            coverage = _coverage(query, window)
            if shape == "default" and coverage < 0.3:
                continue
            weighted = _weighted_coverage(query, window, weights)
            phrase = _weighted_bigram_coverage(query, window, bigram_weights)
            pre_score = (
                0.6 * weighted
                + 0.4 * phrase
                + 0.15 * min(hit_score, 1.2)
                + (0.10 if shape != "default" else 0.0)
                + (0.20 if is_list else 0.0)
            )
            windows.append(
                (pre_score, shape, coverage, hit, window, is_list, weighted, phrase)
            )
        # Mỗi chunk chỉ giữ tối đa 2 cửa sổ tốt nhất; cửa sổ danh sách
        # được giữ thêm để không bị mục cuối danh sách chiếm chỗ.
        windows.sort(key=lambda item: item[0], reverse=True)
        keep = windows[:2]
        for item in windows:
            if item[5] and item not in keep:
                keep.append(item)
        candidates.extend(keep)

    candidates.sort(key=lambda item: item[0], reverse=True)
    candidates = candidates[:40] + [
        item for item in candidates[40:]
        if item[5] and item[1] == "default"
    ][:10]

    if candidates and use_reranker and reranker is not None and reranker.enabled:
        rerank_scores = reranker.score_pairs(
            query, [candidate[4] for candidate in candidates]
        )
        candidates = [
            (pre, shape, coverage, hit, window, score, weighted, phrase, is_list)
            for (pre, shape, coverage, hit, window, is_list, weighted, phrase), score
            in zip(candidates, rerank_scores)
        ]
    else:
        candidates = [
            (pre, shape, coverage, hit, window, pre, weighted, phrase, is_list)
            for (pre, shape, coverage, hit, window, is_list, weighted, phrase)
            in candidates
        ]

    def final_score(candidate: Tuple[Any, ...]) -> float:
        if candidate[1] != "default":
            return candidate[5]
        # Với câu hỏi mở, cộng tín hiệu cụm từ hiếm, ưu tiên cửa sổ bắt
        # đầu danh sách và cửa sổ mở đầu bằng đúng điều khoản.
        heading_bonus = 1.5 if re.match(
            r"(?i)(?:điều|dieu|chương|chuong|mục|muc)\s+\d+",
            candidate[4].lstrip(),
        ) else 0.0
        return (
            candidate[5]
            + 1.2 * candidate[7]
            + 0.4 * candidate[6]
            + (1.5 if candidate[8] else 0.0)
            + heading_bonus
        )

    gate_active = use_reranker and reranker is not None and reranker.enabled

    def passes_gate(candidate: Tuple[Any, ...]) -> bool:
        # Raw cross-encoder score: the bonuses in final_score only rank windows.
        return not gate_active or candidate[5] >= settings.RERANK_GATE

    candidates.sort(key=final_score, reverse=True)

    if any(marker in folded_query for marker in ("gom nhung", "tieu chi", "cac buoc", "bao gom", "gom")):
        list_candidates = [
            candidate for candidate in candidates
            if candidate[1] == "default"
            and candidate[8]
            and passes_gate(candidate)
        ]
        if list_candidates:
            first = list_candidates[0]
            candidates = [first] + [
                candidate for candidate in candidates if candidate is not first
            ]

    if not candidates:
        return []
    best = candidates[0]
    intent = best[1]
    best_score = final_score(best)
    if not passes_gate(best):
        return []

    limit = {
        "meeting": 1,
        "article": 1,
        "count": 1,
        "time": 2,
        "ratio": 2,
        "yesno": 1,
        "who": 1,
        "default": min(top_k, 3),
    }.get(intent, 1)
    if settings.ANSWER_DOMAIN_RULES:
        limit = rules.citation_limit(folded_query, intent, limit)

    # Câu hỏi mở cần các đoạn gần điểm tốt nhất; câu hỏi có dạng trả lời rõ
    # ràng chỉ lấy thêm đoạn thực sự sát điểm cao nhất.
    margin = 2.5 if intent == "default" else 2.0
    selected: List[Dict[str, Any]] = []
    selected_chunks = set()
    for candidate in candidates:
        if final_score(candidate) < best_score - margin:
            break
        if not passes_gate(candidate):
            continue
        hit = candidate[3]
        chunk_id = hit.get("chunk_id")
        if chunk_id in selected_chunks:
            continue
        selected_chunks.add(chunk_id)
        selected.append({**hit, "answer_window": candidate[4]})
        if len(selected) >= limit:
            break
    return selected
