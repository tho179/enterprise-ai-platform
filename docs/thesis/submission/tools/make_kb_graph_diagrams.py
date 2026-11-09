"""Diagrams for Chapter 4: KB1/KB2 architecture, RAG in/out, and the one-page KB output."""
from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parent.parent / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

FONT_DIR = Path(r"C:\Windows\Fonts")
ARIAL = FONT_DIR / "arial.ttf"
ARIAL_BOLD = FONT_DIR / "arialbd.ttf"
CONSOLA = FONT_DIR / "consola.ttf"
CONSOLA_BOLD = FONT_DIR / "consolab.ttf"

TEXT = "#202124"
MUTED = "#5F6368"
WHITE = "#FFFFFF"
BLUE = ("#E8F0FE", "#1A73E8")
GREEN = ("#E6F4EA", "#137333")
ORANGE = ("#FEF7E0", "#B06000")
PURPLE = ("#F3E8FD", "#7B1FA2")
RED = ("#FCE8E6", "#C5221F")
GRAY = ("#F1F3F4", "#5F6368")


def font(size: int, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    path = (CONSOLA_BOLD if bold else CONSOLA) if mono else (ARIAL_BOLD if bold else ARIAL)
    return ImageFont.truetype(str(path), size)


def draw_box(d: ImageDraw.ImageDraw, xy, title=None, body=None, colors=BLUE, title_size=24, body_size=19):
    fill, outline = colors
    d.rounded_rectangle(xy, radius=16, fill=fill, outline=outline, width=3)
    x1, y1, x2, y2 = xy
    if title:
        d.text(((x1 + x2) // 2, y1 + 34), title, font=font(title_size, True), fill=outline, anchor="mm")
    if body:
        d.multiline_text(((x1 + x2) // 2, (y1 + (34 if title else 0) + y2) // 2 + 8), body,
                         font=font(body_size), fill=TEXT, anchor="mm", align="center", spacing=6)


def arrow(d: ImageDraw.ImageDraw, start, end, color="#1A73E8", width=4, label=None, label_offset=(0, -22)):
    x1, y1 = start
    x2, y2 = end
    d.line([start, end], fill=color, width=width)
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    size = 15
    p1 = (x2 - size * math.cos(angle - math.pi / 6), y2 - size * math.sin(angle - math.pi / 6))
    p2 = (x2 - size * math.cos(angle + math.pi / 6), y2 - size * math.sin(angle + math.pi / 6))
    d.polygon([end, p1, p2], fill=color)
    if label:
        mx, my = (x1 + x2) / 2 + label_offset[0], (y1 + y2) / 2 + label_offset[1]
        d.text((mx, my), label, font=font(17), fill=MUTED, anchor="mm")


def title_bar(img: Image.Image, title: str, subtitle: str) -> ImageDraw.ImageDraw:
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, img.width, 110], fill="#0B2A4A")
    d.text((img.width // 2, 40), title, font=font(36, True), fill=WHITE, anchor="mm")
    d.text((img.width // 2, 82), subtitle, font=font(20), fill="#D2E3FC", anchor="mm")
    return d


def kb_sources_arch():
    w, h = 2100, 980
    img = Image.new("RGB", (w, h), WHITE)
    d = title_bar(img, "Hai đường nạp tri thức: KB1 (PDF) và KB2 (link)",
                  "Cùng một schema Document → Chunk → Entity; gộp thành KB bằng ID theo nội dung")

    # sources
    draw_box(d, (60, 180, 430, 380), "KB1 — PDF nội bộ", "35 tệp · 395 trang\nĐiều lệ, quy chế, quy trình", GREEN, 25, 20)
    draw_box(d, (60, 600, 430, 800), "KB2 — Link công khai", "10 URL · 24.281 ký tự\nGiới thiệu, quản trị, tài liệu", ORANGE, 25, 20)

    # loaders
    draw_box(d, (520, 180, 850, 380), "PDF loader", "extract_text_from_pdf\n+ OCR fallback\nAdaptiveChunker", BLUE, 23, 18)
    draw_box(d, (520, 600, 850, 800), "Link loader", "httpx + HTMLParser\nbỏ nav/script/style\nAdaptiveChunker", BLUE, 23, 18)

    # KBs
    draw_box(d, (950, 180, 1240, 380), "KB1", "Neo4j\nKnowledgeBase", PURPLE, 25, 19)
    draw_box(d, (950, 600, 1240, 800), "KB2", "Neo4j\nKnowledgeBase", PURPLE, 25, 19)

    # merged KB and RAG
    draw_box(d, (1370, 360, 1660, 620), "KB", "hợp nhất\nKB1 + KB2\n\nMERGED_INTO", RED, 27, 19)
    draw_box(d, (1770, 360, 2050, 620), "RAG", "vector + graph\nRRF → rerank\nanswer + citation", BLUE, 25, 18)

    arrow(d, (430, 280), (520, 280), label="nạp")
    arrow(d, (430, 700), (520, 700), label="fetch")
    arrow(d, (850, 280), (950, 280), label="MERGE")
    arrow(d, (850, 700), (950, 700), label="MERGE")
    arrow(d, (1240, 300), (1370, 430), label="HAS_DOCUMENT")
    arrow(d, (1240, 680), (1370, 550), label="HAS_DOCUMENT")
    arrow(d, (1660, 490), (1770, 490), label="truy vấn")

    d.text((60, 880), "ID = băm(nội dung + tiêu đề). Nạp lại không tạo bản trùng; cùng tài liệu ở KB1 và KB2 dùng chung node.",
           font=font(19), fill=MUTED, anchor="lm")
    img.save(ASSETS / "kb_graph_sources.png", quality=95)
    print("wrote kb_graph_sources.png")


def rag_kb_in_out():
    w, h = 2200, 1180
    img = Image.new("RGB", (w, h), WHITE)
    d = title_bar(img, "RAG kết nối KB: IN → truy xuất → OUT",
                  "Vector tìm đoạn giống câu hỏi; đồ thị tìm đoạn chứa cùng thực thể; RRF hợp nhất")

    # IN
    draw_box(d, (50, 180, 380, 430), "IN", "query\ntop_k = 5\nmin_score = 0.3\ndocument_id = null", ORANGE, 26, 18)
    draw_box(d, (470, 230, 760, 380), "Embedding", "E5-Small\n384 chiều", GREEN, 23, 18)

    # two retrieval channels
    draw_box(d, (870, 150, 1240, 320), "Qdrant (vector)", "dense + lexical\narticle boost\ntop-k ứng viên", BLUE, 23, 18)
    draw_box(d, (870, 390, 1240, 560), "Neo4j (graph)", "Entity → Chunk\ntheo Điều / chức danh\n1-hop", PURPLE, 23, 18)

    # fusion and rerank
    draw_box(d, (1350, 230, 1640, 450), "RRF", "k = 60\ngraph_weight = 0.5\nhợp nhất hai danh sách", RED, 24, 17)
    draw_box(d, (1740, 230, 2040, 450), "Rerank", "cross-encoder\n10 ứng viên\nchấm lại cặp (q, passage)", ORANGE, 24, 17)

    # answer gate and outputs
    draw_box(d, (1350, 650, 1640, 850), "Answer gate", "coverage ≥ 0.3\nrerank gate\ncitation bắt buộc", GRAY, 24, 17)
    draw_box(d, (1740, 600, 2140, 780), "OUT — trả lời", "answer + citations\npages / section_path\nmodel_used", GREEN, 25, 18)
    draw_box(d, (1740, 870, 2140, 1050), "OUT — từ chối", "answer = “chưa tìm thấy...”\ncitations = []\nkhông suy diễn", RED, 25, 18)

    arrow(d, (380, 305), (470, 305), label="vector hóa")
    arrow(d, (760, 290), (870, 235), label="dense")
    arrow(d, (760, 330), (870, 455), label="entity")
    arrow(d, (1240, 235), (1350, 300), label="rank 1..k")
    arrow(d, (1240, 455), (1350, 390), label="rank 1..m")
    arrow(d, (1640, 340), (1740, 340), label="top-10")
    arrow(d, (1890, 450), (1600, 650), label="đủ tin cậy?", label_offset=(80, -15))
    arrow(d, (1640, 720), (1740, 690), label="có")
    arrow(d, (1640, 790), (1740, 930), label="không")

    d.text((50, 1100), "Nếu câu hỏi không có thực thể đã biết, graph trả [] và RAG tiếp tục với vector — không làm gãy luồng trả lời.",
           font=font(19), fill=MUTED, anchor="lm")
    img.save(ASSETS / "rag_kb_in_out.png", quality=95)
    print("wrote rag_kb_in_out.png")


KB_JSON = """{
  "doc": {
    "doc_id": "doc-61fde4771461df6e",
    "title": "Quy che hoat dong HDQT",
    "source_uri": ".../Quy_che_hoat_dong_HDQT.pdf",
    "source_type": "pdf",
    "content_hash": "86a877ba...",
    "page_count": 15,
    "char_count": 37896,
    "version": 1,
    "is_current": true
  },
  "chunks": [
    {
      "chunk_id": "chk-a45f54d21187c278",
      "chunk_index": 30,
      "page_start": 5,
      "page_end": 5,
      "section_path": ["CHƯƠNG II", "Điều 8. Chủ tịch, Phó Chủ tịch HĐQT"],
      "text": "Chủ tịch HĐQT có quyền lập chương trình, chuẩn bị tài liệu họp...",
      "content_hash": "a33ffd69...",
      "entities": [
        {"entity_id": "ent-9b3d...", "name": "Chủ tịch HĐQT", "type": "chuc_danh"},
        {"entity_id": "ent-e532...", "name": "HĐQT", "type": "chuc_danh"}
      ]
    }
  ],
  "entities": [
    {"entity_id": "ent-9b3d...", "name": "Chủ tịch HĐQT", "type": "chuc_danh"},
    {"entity_id": "ent-e532...", "name": "HĐQT", "type": "chuc_danh"},
    {"entity_id": "ent-c096...", "name": "ĐHĐCĐ", "type": "chuc_danh"}
  ]
}"""


def _wrap(d: ImageDraw.ImageDraw, text: str, fnt, max_width: int) -> list[str]:
    words = text.split(" ")
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if d.textlength(candidate, font=fnt) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _draw_json(d: ImageDraw.ImageDraw, text: str, x: int, y: int, width: int) -> int:
    body = font(21, mono=True)
    key_font = font(21, bold=True, mono=True)
    line_h = 30
    for raw in text.splitlines():
        line = raw
        if len(line) > 84:
            line = line[:81] + "..."
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        px = x + indent * 10
        match = re.match(r'("(?:[^"\\]|\\.)*")(\s*:)(.*)$', stripped)
        if match:
            d.text((px, y), match.group(1), font=key_font, fill="#1A73E8")
            key_w = d.textlength(match.group(1), font=key_font)
            d.text((px + key_w, y), match.group(2), font=body, fill="#5F6368")
            rest = match.group(3)
            d.text((px + key_w + d.textlength(match.group(2), font=body), y), rest, font=body, fill="#202124")
        else:
            color = "#5F6368" if stripped[:1] in "{}[]" else "#202124"
            d.text((px, y), stripped, font=body, fill=color)
        y += line_h
    return y


def kb_output_one_page():
    w, h = 1654, 2339  # A4 @ 200 dpi
    img = Image.new("RGB", (w, h), WHITE)
    d = ImageDraw.Draw(img)

    # header
    d.rectangle([0, 0, w, 150], fill="#0B2A4A")
    d.text((60, 48), "KB OUTPUT — BẢN GHI TRI THỨC CHUẨN", font=font(32, True), fill=WHITE)
    d.text((60, 96), "Document → Chunk → Entity → Quan hệ → Thống kê", font=font(20), fill="#D2E3FC")

    # JSON panel
    panel = (55, 185, 1075, 1320)
    d.rounded_rectangle(panel, radius=14, fill="#F8F9FA", outline="#DADCE0", width=2)
    d.text((80, 205), "kb_sample.json  (rút gọn, đã làm sạch lỗi OCR để dễ đọc)", font=font(17, True, mono=True), fill=MUTED)
    y = _draw_json(d, KB_JSON, 80, 245, 960)

    # callouts
    callouts = [
        ("1", "doc", "Metadata tài liệu:\ndoc_id, source_uri,\ncontent_hash, version,\nis_current."),
        ("2", "chunks[]", "Đơn vị truy xuất:\nchunk_id, trang, section_path,\ntext, content_hash,\nentities[]."),
        ("3", "entities[]", "Thực thể unique toàn KB:\nĐiều khoản, chức danh,\nmốc thời gian."),
        ("4", "relations", "Cạnh LPG do schema.py sinh:\nHAS_DOCUMENT, HAS_CHUNK,\nMENTIONS."),
        ("5", "stats", "store.stats() sau khi ghi:\nsố document/chunk/entity;\ndùng kiểm tra lô."),
        ("6", "kb_id", "Tham số đích khi ghi:\nKB1, KB2 hoặc KB;\nkhông nằm trong record."),
    ]
    cy = 195
    for number, name, desc in callouts:
        d.ellipse([1110, cy, 1155, cy + 45], fill="#1A73E8")
        d.text((1132, cy + 22), number, font=font(21, True), fill=WHITE, anchor="mm")
        d.text((1170, cy - 2), name, font=font(20, True, mono=True), fill="#137333")
        for i, line in enumerate(desc.split("\n")):
            d.text((1170, cy + 28 + i * 25), line, font=font(17), fill=TEXT)
        cy += 185

    # graph strip
    gy = 1360
    d.text((60, gy), "Quan hệ do schema.py sinh (4 node · 3 cạnh)", font=font(18, True), fill="#0B2A4A")
    boxes = [
        (60, gy + 40, 300, gy + 150, "KB1", "KnowledgeBase", PURPLE),
        (390, gy + 40, 700, gy + 150, "Document", "doc-61fde...", BLUE),
        (790, gy + 40, 1100, gy + 150, "Chunk", "chk-a45f...", GREEN),
        (1190, gy + 40, 1500, gy + 150, "Entity", "Chủ tịch HĐQT", ORANGE),
    ]
    for x1, y1, x2, y2, title, sub, colors in boxes:
        draw_box(d, (x1, y1, x2, y2), title, sub, colors, 22, 16)
    arrow(d, (300, gy + 95), (390, gy + 95), label="HAS_DOCUMENT", label_offset=(0, -28))
    arrow(d, (700, gy + 95), (790, gy + 95), label="HAS_CHUNK", label_offset=(0, -28))
    arrow(d, (1100, gy + 95), (1190, gy + 95), label="MENTIONS", label_offset=(0, -28))

    # stats strip
    d.rounded_rectangle([55, 1535, 1599, 1598], radius=12, fill="#E8F0FE", outline="#1A73E8", width=2)
    d.text((80, 1567), 'store.stats("KB1")  →  {"documents": 1, "chunks": 70, "entities": 26}',
           font=font(18, True, mono=True), fill="#0B2A4A", anchor="lm")

    # reading guide
    box_top = 1625
    d.rounded_rectangle([55, box_top, 1599, 2085], radius=14, fill="#F1F8E9", outline="#7CB342", width=2)
    d.text((80, box_top + 22), "Cách đọc bản ghi này trong 6 dòng", font=font(21, True), fill="#33691E")
    notes = [
        "1. `doc.doc_id` là khóa theo nội dung: sửa nội dung → đổi ID; nạp lại cùng nội dung → không tạo bản trùng.",
        "2. `chunks[]` là đơn vị RAG dùng để trích dẫn; `page_start/page_end` + `section_path` đủ để mở đúng vị trí trong PDF.",
        "3. `entities[]` cấp record là danh sách unique; mỗi chunk cũng giữ `entities[]` để biết đoạn nào nhắc thực thể nào.",
        "4. `relations` không nằm trong JSON thô: `store.upsert_record` sinh cạnh từ `schema.py`; `kb_id` là tham số đích khi ghi.",
        "5. `stats` do `store.stats()` tính sau khi ghi/gộp, dùng để kiểm tra số document/chunk/entity của lô.",
        "6. `is_current = false` là bản lịch sử; RAG chỉ dùng bản current nhưng vẫn truy vết được phiên bản cũ.",
    ]
    for i, line in enumerate(notes):
        d.text((80, box_top + 70 + i * 52), line, font=font(17), fill=TEXT)

    # footer
    d.line([55, 2185, 1599, 2185], fill="#DADCE0", width=2)
    d.text((60, 2215), "Hình 4.6 — Dạng KB output một trang. Nguồn: debug/kb_sample.json;",
           font=font(17), fill=MUTED)
    d.text((60, 2245), "số liệu chunk/entity lấy từ lần dry-run Quy_che_hoat_dong_HDQT.pdf (15 trang).",
           font=font(17), fill=MUTED)

    img.save(ASSETS / "kb_output_one_page.png", quality=95)
    print("wrote kb_output_one_page.png")


if __name__ == "__main__":
    kb_sources_arch()
    rag_kb_in_out()
    kb_output_one_page()
