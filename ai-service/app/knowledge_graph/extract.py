"""Turn a PDF or a web page into the node/chunk/entity record used by Neo4j."""
from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

try:
    from app.adaptive_chunker import AdaptiveChunker
    from app.document_parser import extract_text_from_pdf
except ImportError:  # scripts run with ai-service/ on sys.path
    from adaptive_chunker import AdaptiveChunker
    from document_parser import extract_text_from_pdf

from .ids import chunk_id, document_id, entity_id, fold, sha1_text

# Case-sensitive on purpose: "phần vốn góp" and "điều lệ." are ordinary text.
# Lowercase l is kept because OCR reads "Điều 1" as "Điều l".
HEADING_RE = re.compile(
    r"^(CHƯƠNG|Chương|PHẦN|Phần|MỤC|Mục|ĐIỀU|Điều)\s+([IVXLC]+|l|\d+)(?![^\W\d_])\s*[\.:\-–]?\s*(.*)$"
)
# Policy documents number their sections instead: "VI. HIỆU LỰC", "5.1 QUY TRÌNH".
NUMBERED_HEADING_RE = re.compile(r"^((?:[IVX]+\.)|(?:\d+(?:\.\d+)*\.?))\s+(\S.*)$")
ARTICLE_RE = re.compile(r"\bĐiều\s+(\d{1,3})\b", re.IGNORECASE)
DATE_RE = re.compile(r"\bngày\s+(\d{1,2})[/-](\d{1,2})[/-](\d{4})", re.IGNORECASE)
LAW_RE = re.compile(r"\b(Bộ luật|Luật)\s+([^\W\d_]+(?:\s+[^\W\d_]+)?)")
DECREE_RE = re.compile(
    r"\b(Nghị định|Thông tư)\s+(?:số\s+)?(\d+/\d{4}/[^\s,.;)]+)",
    re.IGNORECASE,
)
HEADING_TITLE_RE = re.compile(
    r"^(?:CHƯƠNG|Chương|PHẦN|Phần|MỤC|Mục|ĐIỀU|Điều)\s+(?:[IVXLC]+|l|\d+)\s*[\.:\-–]*\s*(.+)$",
)
ARTICLE_HEADING_RE = re.compile(r"^\s*(?:ĐIỀU|Điều)\s+(\d{1,3})\b")
EXTERNAL_LAW_RE = re.compile(r"Bộ luật|Luật|Nghị định|Thông tư")
LAW_STOPWORDS = {"và", "số", "này", "của", "có", "về", "hoặc", "theo", "định", "pháp"}

# Numbered entities repeat in every document, so they never bridge documents.
LOCAL_ENTITY_TYPES = ("dieu_khoan", "moc_thoi_gian")

# Canonical name -> (kind, aliases). Aliases are matched case-insensitively.
ROLE_ALIASES = {
    "Chủ tịch Hội đồng Quản trị": ("chuc_danh", ["Chủ tịch Hội đồng Quản trị", "Chủ tịch HĐQT"]),
    "Hội đồng Quản trị": ("chuc_danh", ["Hội đồng Quản trị", "HĐQT"]),
    "Tổng Giám đốc": ("chuc_danh", ["Tổng Giám đốc", "Tổng giám đốc", "TGĐ"]),
    "Ban Kiểm soát": ("chuc_danh", ["Ban Kiểm soát", "Ban kiểm soát", "BKS"]),
    "Đại hội đồng cổ đông": ("chuc_danh", ["Đại hội đồng cổ đông", "ĐHĐCĐ"]),
    "Ủy ban Kiểm toán": ("chuc_danh", ["Ủy ban Kiểm toán", "Ủy ban kiểm toán"]),
    "Người đại diện theo pháp luật": ("chuc_danh", ["Người đại diện theo pháp luật"]),
    "Kế toán trưởng": ("chuc_danh", ["Kế toán trưởng"]),
    "Kiểm soát viên": ("chuc_danh", ["Kiểm soát viên"]),
    "Công đoàn": ("chuc_danh", ["Công đoàn"]),
    "Người sử dụng lao động": ("chuc_danh", ["Người sử dụng lao động", "NSDLĐ"]),
    "Người lao động": ("chuc_danh", ["Người lao động", "NLĐ"]),
}

# Domain terms give graph retrieval signal for questions that contain no role,
# article number, or date. Keep this list curated: each alias becomes a graph
# entity and a co-mention edge, so noisy generic words hurt more than they help.
TOPIC_ALIASES = {
    "Cổ tức": ("chu_de", ["cổ tức"]),
    "Cổ phần": ("chu_de", ["cổ phần", "cổ phiếu"]),
    "Vốn điều lệ": ("chu_de", ["vốn điều lệ"]),
    "Trái phiếu": ("chu_de", ["trái phiếu"]),
    "Hợp đồng lao động": ("chu_de", ["hợp đồng lao động"]),
    "Tiền lương": ("chu_de", ["tiền lương", "mức lương"]),
    "Bảo hiểm xã hội": ("chu_de", ["bảo hiểm xã hội", "BHXH"]),
    "Nghỉ hằng năm": ("chu_de", ["nghỉ hằng năm", "nghỉ phép"]),
    "An toàn thông tin": ("chu_de", ["an toàn thông tin", "bảo mật thông tin"]),
    "Dữ liệu cá nhân": ("chu_de", ["dữ liệu cá nhân"]),
    "Quyền truy cập": ("chu_de", ["quyền truy cập"]),
    "Sự cố": ("chu_de", ["sự cố"]),
    "Đào tạo": ("chu_de", ["đào tạo"]),
    "Kỷ luật": ("chu_de", ["kỷ luật"]),
}

ENTITY_ALIASES = {**ROLE_ALIASES, **TOPIC_ALIASES}


def _is_heading(line: str) -> bool:
    match = HEADING_RE.match(line)
    # "Điều 51 của Điều lệ này..." is a sentence that happens to start the line.
    return bool(match) and not match.group(3)[:1].islower()


def _heading_level(match: re.Match) -> int:
    word = match.group(1).upper()
    if word in ("CHƯƠNG", "PHẦN"):
        return 1
    if word == "MỤC":
        return 2
    return 3


def _numbered_heading_level(line: str) -> Optional[int]:
    """Level of an uppercase numbered title; None for ordinary numbered clauses."""
    match = NUMBERED_HEADING_RE.match(line)
    if not match:
        return None
    title = match.group(2)
    letters = [char for char in title if char.isalpha()]
    if len(title.split()) < 2 or len(letters) < 6 or not all(char.isupper() for char in letters):
        return None
    number = match.group(1).rstrip(".")
    return 1 if not number[0].isdigit() else number.count(".") + 2


def _level_of(page_text: str, use_numbered: bool, block: str) -> Optional[int]:
    if _is_heading(block):
        return _heading_level(HEADING_RE.match(block))
    return _numbered_heading_level(block) if use_numbered else None


def _blocks(text: str) -> List[str]:
    """Split page text into headings and paragraphs without losing line joins."""
    blocks: List[str] = []
    buffer: List[str] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            if buffer:
                blocks.append(" ".join(buffer))
                buffer = []
            continue
        if _is_heading(line) or _numbered_heading_level(line) is not None:
            if buffer:
                blocks.append(" ".join(buffer))
                buffer = []
            blocks.append(line)
        else:
            buffer.append(line)
    if buffer:
        blocks.append(" ".join(buffer))
    return blocks


def pages_to_nodes(pages: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build the structure-aware nodes consumed by AdaptiveChunker."""
    pages = list(pages)
    # A document with Chương/Điều keeps numbered clauses as body text.
    use_numbered = not any(
        _is_heading(line.strip())
        for page in pages
        for line in (page.get("text") or "").splitlines()
    )
    nodes: List[Dict[str, Any]] = []
    section: List[tuple] = []  # (level, title), shallowest first
    in_toc = False
    for page in pages:
        for block in _blocks(page.get("text", "")):
            # Phát hiện Mục lục (TOC) và chuỗi chấm dẫn trang để loại bỏ
            is_toc_item = bool(re.search(r"(?:\.{4,}|…{2,}|_{4,}|-{4,})", block))
            has_toc_keyword = bool(re.search(r"(?i)\b(?:mục lục|table of contents|muc luc)\b", block))

            if has_toc_keyword or is_toc_item:
                in_toc = True

            if in_toc:
                # Thoát khỏi vùng TOC nếu gặp Điều 1 hoặc Chương chính thức và không có chuỗi chấm
                if not is_toc_item and re.match(r"(?i)^(chương\s+[i1vxlcdm\d]|phần\s+[i1vxlcdm\d]|điều\s+1[\.\:\-])", block):
                    in_toc = False

            if in_toc or is_toc_item or has_toc_keyword:
                nodes.append(
                    {
                        "text": block,
                        "page": int(page.get("page", 1)),
                        "section_path": [title for _, title in section],
                        "block_type": "TOC",
                        "is_garbage": True,
                    }
                )
                continue

            level = _level_of(page.get("text", ""), use_numbered, block)
            if level is not None:
                section = [item for item in section if item[0] < level] + [(level, block[:160])]
            nodes.append(
                {
                    "text": block,
                    "page": int(page.get("page", 1)),
                    "section_path": [title for _, title in section],
                    "block_type": "TEXT",
                    "is_garbage": False,
                }
            )
    return nodes


def extract_entities(text: str) -> List[Dict[str, str]]:
    """Baseline rule-based NER: articles, roles and explicit dates."""
    found: Dict[str, Dict[str, str]] = {}

    for match in ARTICLE_RE.finditer(text or ""):
        name = f"Điều {match.group(1)}"
        eid = entity_id(name, "dieu_khoan")
        found[eid] = {"entity_id": eid, "name": name, "type": "dieu_khoan"}

    for canonical, (kind, aliases) in ENTITY_ALIASES.items():
        if any(alias.casefold() in (text or "").casefold() for alias in aliases):
            eid = entity_id(canonical, kind)
            found[eid] = {"entity_id": eid, "name": canonical, "type": kind}

    for match in DATE_RE.finditer(text or ""):
        name = f"{match.group(1)}/{match.group(2)}/{match.group(3)}"
        eid = entity_id(name, "moc_thoi_gian")
        found[eid] = {"entity_id": eid, "name": name, "type": "moc_thoi_gian"}

    for match in LAW_RE.finditer(text or ""):
        words = match.group(2).split()
        if not words[0][0].isupper() or words[0].casefold() in LAW_STOPWORDS:
            continue
        if len(words) > 1 and words[1].casefold() in LAW_STOPWORDS:
            words = words[:1]
        name = " ".join([match.group(1), *words])
        eid = entity_id(name, "van_ban")
        found[eid] = {"entity_id": eid, "name": name, "type": "van_ban"}

    for match in DECREE_RE.finditer(text or ""):
        name = f"{match.group(1).capitalize()} {match.group(2)}"
        eid = entity_id(name, "van_ban")
        found[eid] = {"entity_id": eid, "name": name, "type": "van_ban"}

    return sorted(found.values(), key=lambda item: (item["type"], item["name"]))


def heading_entity(section_path: List[str]) -> Optional[Dict[str, str]]:
    """The title of the chunk's own section, as a corpus-independent topic."""
    if not section_path:
        return None
    leaf = str(section_path[-1]).strip()
    match = HEADING_TITLE_RE.match(leaf) or NUMBERED_HEADING_RE.match(leaf)
    if not match:
        return None
    title = re.sub(r"\s+", " ", match.group(match.lastindex)).strip(" .:;-–")
    if not 2 <= len(title.split()) <= 12:
        return None
    if title.isupper():
        title = title.capitalize()
    folded = fold(title)
    for canonical, (_kind, aliases) in ENTITY_ALIASES.items():
        if folded in {fold(canonical), *(fold(alias) for alias in aliases)}:
            return None  # already covered by the canonical entity
    eid = entity_id(title, "tieu_de")
    return {"entity_id": eid, "name": title, "type": "tieu_de"}


def own_article(section_path: List[str], text: str) -> Optional[str]:
    for item in reversed(section_path or []):
        match = ARTICLE_HEADING_RE.match(str(item))
        if match:
            return match.group(1)
    match = ARTICLE_HEADING_RE.match(text or "")
    return match.group(1) if match else None


def link_chunks(chunks: List[Dict[str, Any]]) -> None:
    """Add heading topics, APPLIES_TO targets and same-document REFERENCES."""
    articles: Dict[str, List[str]] = {}
    for chunk in chunks:
        number = own_article(chunk["section_path"], chunk["text"])
        chunk["own_article"] = number
        if number:
            articles.setdefault(number, []).append(chunk["chunk_id"])

    for chunk in chunks:
        topic = heading_entity(chunk["section_path"])
        if topic and all(e["entity_id"] != topic["entity_id"] for e in chunk["entities"]):
            chunk["entities"] = [*chunk["entities"], topic]

        heading = " ".join(str(item) for item in chunk["section_path"][-1:])
        applies = {
            entity["entity_id"]
            for entity in extract_entities(heading)
            if entity["type"] not in LOCAL_ENTITY_TYPES
        }
        if topic:
            applies.add(topic["entity_id"])
        chunk["applies_to"] = sorted(applies)

        references: Dict[str, str] = {}
        for match in ARTICLE_RE.finditer(chunk["text"]):
            number = match.group(1)
            if number == chunk["own_article"]:
                continue
            if EXTERNAL_LAW_RE.search(chunk["text"][match.end():match.end() + 40]):
                continue  # "Điều 5 Luật Doanh nghiệp" is not this document's Điều 5
            for target in articles.get(number, [])[:2]:
                if target != chunk["chunk_id"]:
                    references[target] = f"Điều {number}"
        chunk["references"] = [
            {"target": target, "article": article}
            for target, article in sorted(references.items())
        ]


def build_record_from_pages(
    title: str,
    source_uri: str,
    source_type: str,
    pages: List[Dict[str, Any]],
    chunker: Optional[AdaptiveChunker] = None,
) -> Dict[str, Any]:
    """Pure builder used by both the PDF and the link ingestion paths."""
    pages = [p for p in pages if (p.get("text") or "").strip()]
    full_text = "\n".join(p.get("text", "") for p in pages)
    content_hash = sha1_text(full_text)
    doc_id = document_id(content_hash, title)

    chunker = chunker or AdaptiveChunker()
    chunks = chunker.chunk_nodes(pages_to_nodes(pages))

    chunk_records: List[Dict[str, Any]] = []
    all_entities: Dict[str, Dict[str, str]] = {}
    for index, chunk in enumerate(chunks, start=1):
        entities = extract_entities(chunk.content)
        for entity in entities:
            all_entities[entity["entity_id"]] = entity
        chunk_records.append(
            {
                "chunk_id": chunk_id(doc_id, index, chunk.content),
                "chunk_index": index,
                "text": chunk.content,
                "page_start": int(chunk.metadata.get("page_start", 1)),
                "page_end": int(chunk.metadata.get("page_end", 1)),
                "section_path": list(chunk.metadata.get("section_path") or []),
                "content_hash": sha1_text(chunk.content),
                "entities": entities,
            }
        )

    link_chunks(chunk_records)
    for chunk in chunk_records:
        for entity in chunk["entities"]:
            all_entities[entity["entity_id"]] = entity

    return {
        "doc": {
            "doc_id": doc_id,
            "title": title,
            "source_uri": source_uri,
            "source_type": source_type,
            "content_hash": content_hash,
            "page_count": len(pages),
            "char_count": len(full_text),
            "is_current": True,
            "version": 1,
        },
        "chunks": chunk_records,
        "entities": list(all_entities.values()),
    }


def _as_int(value: Any, default: int = 1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _section_path(value: Any) -> List[str]:
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _chunk_index(chunk: Dict[str, Any], fallback: int) -> int:
    raw = chunk.get("chunk_index")
    if raw is not None:
        return _as_int(raw, fallback)
    match = re.search(r"-c(\d+)$", str(chunk.get("chunk_id") or ""))
    return int(match.group(1)) if match else fallback


def _version_number(metadata: Dict[str, Any], chunk_id_value: str) -> int:
    raw = metadata.get("version_number")
    if raw is not None:
        return _as_int(raw)
    match = re.search(r"-v(\d+)-", chunk_id_value)
    return int(match.group(1)) if match else 1


def build_record_from_ingest_chunks(chunks: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Build graph records from the exact chunks the backend sent to Qdrant.

    The chunk_id is copied verbatim so Neo4j and Qdrant point at the same unit
    of text; this is the bridge that makes graph retrieval citable.
    """
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for chunk in chunks:
        metadata = chunk.get("metadata") or {}
        doc_id = str(metadata.get("document_id") or "").strip()
        if not doc_id:
            continue
        grouped.setdefault(doc_id, []).append(chunk)

    records: List[Dict[str, Any]] = []
    for doc_id, items in grouped.items():
        items = sorted(items, key=lambda item: _chunk_index(item, 0))
        first_meta = items[0].get("metadata") or {}
        title = str(first_meta.get("title") or first_meta.get("document_code") or doc_id)
        max_version = 1
        current_version_id = f"{doc_id}:v1"

        chunk_records: List[Dict[str, Any]] = []
        all_entities: Dict[str, Dict[str, str]] = {}
        seen_chunks = set()
        for position, item in enumerate(items):
            content = str(item.get("content") or "")
            cid = str(item.get("chunk_id") or f"{doc_id}-c{position}")
            if cid in seen_chunks:
                continue
            seen_chunks.add(cid)
            metadata = item.get("metadata") or {}
            item_version = _version_number(metadata, cid)
            item_version_id = str(
                metadata.get("version_id") or f"{doc_id}:v{item_version}"
            )
            if item_version >= max_version:
                max_version = item_version
                current_version_id = item_version_id
            entities = extract_entities(content)
            for entity in entities:
                all_entities[entity["entity_id"]] = entity
            chunk_records.append(
                {
                    "chunk_id": cid,
                    "chunk_index": _chunk_index(item, position),
                    "text": content,
                    "page_start": _as_int(metadata.get("page_start"), 1),
                    "page_end": _as_int(metadata.get("page_end"), 1),
                    "section_path": _section_path(metadata.get("section_path")),
                    "content_hash": sha1_text(content),
                    "version_id": item_version_id,
                    "entities": entities,
                }
            )

        if not chunk_records:
            continue

        link_chunks(chunk_records)
        for chunk in chunk_records:
            for entity in chunk["entities"]:
                all_entities[entity["entity_id"]] = entity

        records.append(
            {
                "doc": {
                    "doc_id": doc_id,
                    "title": title,
                    "source_uri": f"upload:{doc_id}",
                    "source_type": "upload",
                    "content_hash": sha1_text(f"{doc_id}|{current_version_id}"),
                    "page_count": max(chunk["page_end"] for chunk in chunk_records),
                    "char_count": sum(len(chunk["text"]) for chunk in chunk_records),
                    "is_current": True,
                    "version": max_version,
                    "version_id": current_version_id,
                    "document_code": first_meta.get("document_code"),
                    "document_type": first_meta.get("document_type"),
                    "allowed_roles": list(first_meta.get("allowed_roles") or ["*"]),
                },
                "chunks": chunk_records,
                "entities": list(all_entities.values()),
            }
        )
    return records


def build_pdf_record(path, title: Optional[str] = None) -> Dict[str, Any]:
    """Read a PDF with the existing hybrid parser (text layer + OCR fallback)."""
    path_obj = Path(path)
    pages = extract_text_from_pdf(str(path_obj))
    if not pages:
        raise ValueError(f"Không trích xuất được nội dung: {path_obj}")
    return build_record_from_pages(
        title=title or path_obj.stem.replace("_", " "),
        source_uri=str(path_obj),
        source_type="pdf",
        pages=pages,
    )


class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "iframe", "nav", "header", "footer", "aside", "form"}
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: List[str] = []
        self.parts: List[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag in self.SKIP:
            self._skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in self.SKIP and self._skip_depth:
            self._skip_depth -= 1
        if tag == "title":
            self._in_title = False
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._in_title:
            self.title_parts.append(data)
        else:
            self.parts.append(data)


def html_to_text(html: str) -> tuple[str, str]:
    parser = _TextExtractor()
    parser.feed(html)
    title = re.sub(r"\s+", " ", "".join(parser.title_parts)).strip()
    text = re.sub(r"\n{3,}", "\n\n", "".join(parser.parts))
    text = re.sub(r"[ \t]{2,}", " ", text).strip()
    return title, text


def fetch_html(url: str, timeout: int = 30) -> str:
    import httpx

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "vi-VN,vi;q=0.9,en;q=0.5",
    }
    response = httpx.get(url, headers=headers, follow_redirects=True, timeout=timeout)
    response.raise_for_status()
    return response.text


def build_link_record(url: str, html: Optional[str] = None, title: Optional[str] = None) -> Dict[str, Any]:
    html = html if html is not None else fetch_html(url)
    page_title, text = html_to_text(html)
    if not text:
        raise ValueError(f"Trang không có nội dung văn bản: {url}")
    return build_record_from_pages(
        title=title or page_title or url.rstrip("/").rsplit("/", 1)[-1],
        source_uri=url,
        source_type="web",
        pages=[{"page": 1, "text": text}],
    )


def build_link_records(urls: Iterable[str]) -> List[Dict[str, Any]]:
    records = []
    for url in urls:
        try:
            records.append(build_link_record(url))
        except Exception as exc:  # keep the batch alive; caller reports failures
            records.append({"url": url, "error": str(exc)})
    return records
