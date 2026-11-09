"""Generate thesis diagrams as PNG using Pillow (no Graphviz/Mermaid needed)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parent.parent / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

FONT_DIR = Path(r"C:\Windows\Fonts")
ARIAL = FONT_DIR / "arial.ttf"
ARIAL_BOLD = FONT_DIR / "arialbd.ttf"

TEXT = "#202124"
MUTED = "#5F6368"
BLUE = ("#E8F0FE", "#1A73E8")
GREEN = ("#E6F4EA", "#137333")
ORANGE = ("#FEF7E0", "#B06000")
PURPLE = ("#F3E8FD", "#7B1FA2")
RED = ("#FCE8E6", "#C5221F")
GRAY = ("#F1F3F4", "#5F6368")
WHITE = "#FFFFFF"


def font(size, bold=False):
    return ImageFont.truetype(str(ARIAL_BOLD if bold else ARIAL), size)


def canvas(w, h, title=None, subtitle=None):
    img = Image.new("RGB", (w, h), WHITE)
    d = ImageDraw.Draw(img)
    if title:
        d.text((w // 2, 46), title, font=font(38, True), fill=TEXT, anchor="mm")
    if subtitle:
        d.text((w // 2, 96), subtitle, font=font(22), fill=MUTED, anchor="mm")
    return img, d


def box(d, xy, text, colors=BLUE, size=22, bold_title=None, title_size=24, radius=16):
    x1, y1, x2, y2 = xy
    fill, outline = colors
    d.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=3)
    lines = text.split("\n")
    if bold_title and lines:
        d.text(((x1 + x2) // 2, y1 + 32), lines[0], font=font(title_size, True), fill=outline, anchor="mm")
        body = "\n".join(lines[1:])
        if body:
            d.multiline_text(((x1 + x2) // 2, (y1 + 32 + y2) // 2 + 10), body,
                             font=font(size), fill=TEXT, anchor="mm", align="center", spacing=6)
    else:
        d.multiline_text(((x1 + x2) // 2, (y1 + y2) // 2), text,
                         font=font(size), fill=TEXT, anchor="mm", align="center", spacing=6)


def arrow(d, start, end, label=None, color="#1A73E8", width=4, dashed=False, label_offset=(0, -18)):
    x1, y1 = start
    x2, y2 = end
    if dashed:
        total = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        step = 16
        n = int(total // step)
        for i in range(n):
            t1 = i / n
            t2 = min(1, (i + 0.55) / n)
            d.line([(x1 + (x2 - x1) * t1, y1 + (y2 - y1) * t1),
                    (x1 + (x2 - x1) * t2, y1 + (y2 - y1) * t2)], fill=color, width=width)
    else:
        d.line([start, end], fill=color, width=width)
    # arrowhead
    import math
    ang = math.atan2(y2 - y1, x2 - x1)
    size = 16
    p1 = (x2 - size * math.cos(ang - math.pi / 6), y2 - size * math.sin(ang - math.pi / 6))
    p2 = (x2 - size * math.cos(ang + math.pi / 6), y2 - size * math.sin(ang + math.pi / 6))
    d.polygon([end, p1, p2], fill=color)
    if label:
        mx, my = (x1 + x2) / 2 + label_offset[0], (y1 + y2) / 2 + label_offset[1]
        d.text((mx, my), label, font=font(18), fill=MUTED, anchor="mm")


def bar_chart(filename, title, groups, metrics, values, colors, ymax=100, subtitle=None):
    w, h = 1500, 850
    img, d = canvas(w, h, title, subtitle)
    left, top, right, bottom = 140, 160, 60, 150
    plot_w, plot_h = w - left - right, h - top - bottom
    # axes
    d.line([(left, top), (left, top + plot_h), (left + plot_w, top + plot_h)], fill="#9AA0A6", width=3)
    for i in range(0, 101, 20):
        y = top + plot_h - plot_h * i / ymax
        d.line([(left, y), (left + plot_w, y)], fill="#E8EAED", width=2)
        d.text((left - 18, y), f"{i}", font=font(18), fill=MUTED, anchor="rm")
    n_groups = len(groups)
    n_metrics = len(metrics)
    group_w = plot_w / n_groups
    bar_w = group_w * 0.62 / n_metrics
    for gi, group in enumerate(groups):
        gx = left + gi * group_w + group_w * 0.19
        for mi, metric in enumerate(metrics):
            v = values[gi][mi]
            bh = plot_h * v / ymax
            x1 = gx + mi * bar_w
            y1 = top + plot_h - bh
            x2 = x1 + bar_w * 0.86
            y2 = top + plot_h
            d.rounded_rectangle([x1, y1, x2, y2], radius=6, fill=colors[mi], outline=colors[mi])
            d.text(((x1 + x2) / 2, y1 - 22), f"{v:g}", font=font(18, True), fill=TEXT, anchor="mm")
        d.text((left + gi * group_w + group_w / 2, top + plot_h + 34), group,
               font=font(20), fill=TEXT, anchor="ma")
    # legend
    lx = left + 10
    for mi, metric in enumerate(metrics):
        d.rectangle([lx, top - 48, lx + 26, top - 26], fill=colors[mi])
        d.text((lx + 36, top - 37), metric, font=font(19), fill=TEXT, anchor="lm")
        lx += 36 + d.textlength(metric, font=font(19)) + 40
    img.save(ASSETS / filename, quality=95)
    print("wrote", filename)


def dl_encoder():
    w, h = 1700, 950
    img, d = canvas(w, h, "Bi-encoder: câu hỏi và đoạn văn dùng chung encoder",
                    "Hai nhánh mã hóa độc lập, so sánh bằng cosine")
    box(d, (60, 180, 360, 300), "Câu hỏi\n(Query)", ORANGE, 23)
    box(d, (60, 620, 360, 740), "Đoạn văn\n(Passage)", GREEN, 23)
    box(d, (470, 180, 760, 300), "Tokenizer\n(BPE/WordPiece)", GRAY, 21)
    box(d, (470, 620, 760, 740), "Tokenizer\n(BPE/WordPiece)", GRAY, 21)
    box(d, (880, 300, 1240, 620), "Transformer Encoder\n(shared)\n\nMulti-head\nSelf-attention\n+ FFN", PURPLE, 23)
    box(d, (1360, 180, 1640, 300), "Pooling\nMean + L2", BLUE, 21)
    box(d, (1360, 620, 1640, 740), "Pooling\nMean + L2", BLUE, 21)
    box(d, (1360, 380, 1640, 540), "Cosine\nsimilarity", RED, 24)
    arrow(d, (360, 240), (470, 240))
    arrow(d, (360, 680), (470, 680))
    arrow(d, (760, 240), (880, 360), "mã hóa", label_offset=(0, -30))
    arrow(d, (760, 680), (880, 560), "mã hóa", label_offset=(0, 30))
    arrow(d, (1240, 400), (1360, 250))
    arrow(d, (1240, 520), (1360, 670))
    arrow(d, (1640, 240), (1640, 380), "", label_offset=(70, 0))
    arrow(d, (1640, 680), (1640, 540), "", label_offset=(70, 0))
    d.text((1500, 775), "e_q · e_d", font=font(20), fill=MUTED, anchor="mm")
    img.save(ASSETS / "dl_encoder.png", quality=95)
    print("wrote dl_encoder.png")


def db_architecture():
    w, h = 1800, 1000
    img, d = canvas(w, h, "Kiến trúc dữ liệu đa mô hình của EAKWP",
                    "PostgreSQL là nguồn sự thật; Qdrant là chỉ mục vector; tệp gốc lưu ngoài DB")
    box(d, (60, 220, 340, 360), "React Client\n(Admin / Employee)", ORANGE, 21)
    box(d, (450, 200, 840, 390), "Spring Boot Backend\n\nREST API • JWT • JPA\nIngestion Service", BLUE, 22, "Spring Boot Backend")
    box(d, (980, 110, 1320, 270), "PostgreSQL 15\n\nusers • documents\nversions • chunks\ntasks", GREEN, 21)
    box(d, (980, 330, 1320, 490), "Filesystem\n\nPDF gốc\nSHA-256 + UUID", GRAY, 21)
    box(d, (980, 560, 1320, 720), "AI Service\n\nFastAPI • Embedding\nRAG • Reranker", PURPLE, 21)
    box(d, (1450, 560, 1740, 720), "Qdrant\n\n384-dim\nCosine + HNSW", RED, 21)
    box(d, (450, 560, 780, 700), "Redis 7\n\nCache / Queue\n(chưa dùng)", GRAY, 20)
    box(d, (1450, 790, 1740, 930), "Neo4j\n\nKnowledge Graph\n(thiết kế mở rộng)", GRAY, 19)
    arrow(d, (340, 290), (450, 290), "HTTPS")
    arrow(d, (840, 260), (980, 190), "JDBC")
    arrow(d, (840, 310), (980, 410), "File I/O")
    arrow(d, (840, 350), (980, 640), "REST")
    arrow(d, (1320, 640), (1450, 640), "upsert")
    arrow(d, (640, 390), (640, 560), "dự phòng", dashed=True, color="#9AA0A6")
    arrow(d, (1320, 680), (1450, 860), "đồ thị", dashed=True, color="#9AA0A6")
    d.text((900, 930), "Nguồn sự thật: PostgreSQL + Filesystem   |   Chỉ mục có thể rebuild: Qdrant",
           font=font(19), fill=MUTED, anchor="mm")
    img.save(ASSETS / "db_architecture.png", quality=95)
    print("wrote db_architecture.png")


def db_erd():
    w, h = 1850, 1150
    img, d = canvas(w, h, "ERD các bảng cốt lõi", "Quan hệ logic; mã nguồn hiện tại chưa khai báo khóa ngoại vật lý")
    # boxes
    box(d, (50, 220, 440, 610), "users\n\nid UUID PK\nfull_name\nemail UQ\npassword\nrole\nactive\ncreated_at", GREEN, 19, "users", 24)
    box(d, (530, 120, 940, 620), "documents\n\nid UUID PK\ndocument_code UQ\ntitle\ncategory\ncreated_by\ncreated_at\nupdated_at", BLUE, 19, "documents", 24)
    box(d, (1040, 120, 1480, 690), "document_versions\n\nid UUID PK\ndocument_id\nversion_number\nstatus\nchunk_count\npage_count\nis_current\nfile_hash\nstorage_path\ncreated_at", ORANGE, 18, "document_versions", 23)
    box(d, (1040, 780, 1480, 1100), "document_chunks\n\nid UUID PK\ndocument_id\nversion_id\nchunk_id UQ\nchunk_index\nvector_id\npage_start / page_end\nsection_path", PURPLE, 18, "document_chunks", 23)
    box(d, (530, 760, 940, 1080), "ingestion_tasks\n\nid VARCHAR PK\ndocument_id\nversion_id\nstatus\nstep\nchunk_count\nupdated_at", RED, 18, "ingestion_tasks", 23)
    # relationships
    arrow(d, (440, 400), (530, 360), "1..N", color="#5F6368", label_offset=(0, -18))
    arrow(d, (940, 340), (1040, 340), "1..N", color="#5F6368")
    arrow(d, (1260, 690), (1260, 780), "1..N", color="#5F6368", label_offset=(70, 0))
    arrow(d, (1040, 620), (940, 840), "1..N", color="#5F6368", label_offset=(-55, 0), dashed=True)
    d.text((925, 1125), "Ghi chú: chunk giữ document_id để truy vấn nhanh; mã nguồn hiện tại chưa khai báo khóa ngoại vật lý.",
           font=font(16), fill=MUTED, anchor="mm")
    img.save(ASSETS / "db_erd.png", quality=95)
    print("wrote db_erd.png")


def db_state():
    w, h = 1750, 720
    img, d = canvas(w, h, "Vòng đời phiên bản tài liệu", "Trạng thái nạp và cờ is_current")
    box(d, (90, 260, 390, 390), "PROCESSING\n\nĐang parse / chunk / embed", ORANGE, 21)
    box(d, (650, 160, 1010, 290), "INGESTED\n\nĐã có chunk + vector", GREEN, 21)
    box(d, (650, 450, 1010, 580), "FAILED\n\nLỗi; có thể retry", RED, 21)
    box(d, (1280, 160, 1660, 290), "CURRENT\n\nis_current = true\n(duy nhất mỗi document)", BLUE, 20)
    arrow(d, (390, 325), (650, 225), "thành công")
    arrow(d, (390, 325), (650, 515), "lỗi")
    arrow(d, (700, 450), (360, 390), "retry", color="#9AA0A6", dashed=True, label_offset=(0, -20))
    arrow(d, (1010, 225), (1280, 225), "setCurrent")
    d.text((1280, 390), "Khi có bản mới:\nbản cũ is_current = false\nvà vector cũ bị xóa",
           font=font(18), fill=MUTED, anchor="mm", align="center")
    img.save(ASSETS / "db_state.png", quality=95)
    print("wrote db_state.png")


def kb_layers():
    w, h = 1600, 1000
    img, d = canvas(w, h, "Năm lớp biểu diễn tri thức", "Từ bản gốc đến tri thức thủ tục")
    layers = [
        ("L4 — Thủ tục", "Quy tắc trả lời, trích dẫn, từ chối", "RAG Service + Prompt", RED),
        ("L3 — Quan hệ", "Thực thể, quan hệ, đồ thị", "Neo4j (thiết kế mở rộng)", PURPLE),
        ("L2 — Ngữ nghĩa", "Chunk + embedding 384 chiều", "Qdrant + document_chunks", BLUE),
        ("L1 — Cấu trúc", "Chương, điều, khoản, trang", "section_path / document_sections", ORANGE),
        ("L0 — Bản gốc", "PDF, hash, phiên bản", "Filesystem + document_versions", GREEN),
    ]
    y = 140
    for i, (title, desc, store, colors) in enumerate(layers):
        box(d, (160, y, 1440, y + 130), f"{title}\n{desc}   |   {store}", colors, 21, title, 26)
        if i < len(layers) - 1:
            arrow(d, (800, y + 130), (800, y + 160), "", color="#9AA0A6")
        y += 160
    img.save(ASSETS / "kb_layers.png", quality=95)
    print("wrote kb_layers.png")


def kb_pipeline():
    w, h = 2100, 760
    img, d = canvas(w, h, "Pipeline xây dựng cơ sở tri thức", "Sáu tầng, từ PDF gốc đến vector trong Qdrant")
    stages = [
        ("PDF gốc", "01_pages", GREEN),
        ("Parse + OCR", "text + boxes", ORANGE),
        ("Phân tích block", "02_nodes", GRAY),
        ("Cây cấu trúc", "03_structured", PURPLE),
        ("Adaptive chunk", "04_chunks", BLUE),
        ("Metadata", "05_enriched", ORANGE),
        ("Embedding", "06_embedded", GREEN),
        ("Qdrant", "points", RED),
    ]
    x = 55
    y = 300
    bw = 220
    for i, (title, artifact, colors) in enumerate(stages):
        box(d, (x, y, x + bw, y + 150), title, colors, 21)
        d.text((x + bw / 2, y + 185), artifact, font=font(17), fill=MUTED, anchor="ma")
        if i < len(stages) - 1:
            arrow(d, (x + bw, y + 75), (x + bw + 25, y + 75), "", color="#9AA0A6")
        x += bw + 25
    img.save(ASSETS / "kb_pipeline.png", quality=95)
    print("wrote kb_pipeline.png")


def kb_retrieval():
    w, h = 1800, 1050
    img, d = canvas(w, h, "Pipeline truy xuất lai nhiều tầng", "Vector + lexical + article boost + cross-encoder + shape gate")
    # row 1
    box(d, (50, 150, 300, 270), "Câu hỏi", ORANGE, 22)
    box(d, (370, 150, 650, 270), "Embedding\n384 chiều", BLUE, 21)
    box(d, (720, 150, 1030, 270), "Qdrant top-N\nN = 300..1000", RED, 20)
    box(d, (1100, 150, 1400, 270), "Dedup\n(page, content)", GRAY, 20)
    box(d, (1470, 150, 1750, 270), "Combined\ncos + 0.9·lex\n+ 0.45·article", PURPLE, 18)
    arrow(d, (300, 210), (370, 210))
    arrow(d, (650, 210), (720, 210))
    arrow(d, (1030, 210), (1100, 210))
    arrow(d, (1400, 210), (1470, 210))
    # row 2: snake right -> left
    box(d, (1540, 380, 1760, 510), "Cross-encoder\nrerank top-10", PURPLE, 20)
    box(d, (1180, 380, 1470, 510), "Answer windows\n1–4 câu, ≤ 800 ký tự", BLUE, 20)
    box(d, (790, 380, 1110, 510), "Shape gate\ncount / time / ratio\n/ yesno / who / article", ORANGE, 18)
    box(d, (400, 380, 720, 510), "IDF + bigram\nweighted coverage", GREEN, 19)
    box(d, (50, 380, 330, 510), "Rerank\ncửa sổ", PURPLE, 20)
    arrow(d, (1600, 270), (1600, 380), "", color="#9AA0A6")
    arrow(d, (1540, 445), (1470, 445), "", color="#9AA0A6")
    arrow(d, (1180, 445), (1110, 445), "", color="#9AA0A6")
    arrow(d, (790, 445), (720, 445), "", color="#9AA0A6")
    arrow(d, (400, 445), (330, 445), "", color="#9AA0A6")
    # row 3
    box(d, (50, 630, 360, 760), "Selection\nintent limit + margin", BLUE, 20)
    box(d, (430, 630, 760, 760), "LLM (Gemini/OpenAI)\nhoặc extractive fallback", GREEN, 19)
    box(d, (830, 630, 1160, 760), "Citation\nchunk_id • pages • section", RED, 19)
    box(d, (1230, 630, 1560, 760), "Trả lời / Từ chối\nnếu không đủ căn cứ", ORANGE, 19)
    arrow(d, (190, 510), (190, 630), "", color="#9AA0A6")
    arrow(d, (360, 695), (430, 695), "", color="#9AA0A6")
    arrow(d, (760, 695), (830, 695), "", color="#9AA0A6")
    arrow(d, (1160, 695), (1230, 695), "", color="#9AA0A6")
    d.text((900, 880), "Nguyên tắc: recall rộng ở tầng vector → siết precision bằng shape, coverage, rerank",
           font=font(19), fill=MUTED, anchor="mm")
    img.save(ASSETS / "kb_retrieval.png", quality=95)
    print("wrote kb_retrieval.png")


if __name__ == "__main__":
    dl_encoder()
    bar_chart(
        "dl_benchmark.png",
        "So sánh ba mô hình embedding trên 152 chunk",
        ["E5-Small", "Vietnamese-Bi-Encoder", "MiniLM-L12-v2"],
        ["Recall@3 (%)", "MRR × 100"],
        [[100.0, 90.0], [80.0, 80.0], [80.0, 66.7]],
        ["#1A73E8", "#137333"],
        ymax=100,
        subtitle="Càng cao càng tốt — E5 đạt Recall@3 100% và MRR 0,90",
    )
    db_architecture()
    db_erd()
    db_state()
    kb_layers()
    kb_pipeline()
    kb_retrieval()
    bar_chart(
        "kb_chunking.png",
        "Structure-aware vs fixed-size 1.200/200",
        ["Structure-aware", "Fixed 1.200/200"],
        ["Chunk trộn section (%)", "Kết thúc giữa câu (%)"],
        [[0.0, 7.2], [32.1, 98.2]],
        ["#C5221F", "#B06000"],
        ymax=100,
        subtitle="Structure-aware giữ nguyên ranh giới điều khoản",
    )
