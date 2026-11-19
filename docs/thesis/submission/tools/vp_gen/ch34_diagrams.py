"""Chapter 3-4 diagrams redrawn in Visual Paradigm (same content as the earlier
figures; the L3 row follows the code: graph_search is part of RAG).

    python ch34_diagrams.py <out.xml>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from vpgen import Project, Shape  # noqa: E402

p = Project()


def activity(name):
    d = p.diagram(name, "ActivityDiagram")
    N = {}

    def node(key, kind, label, x, y, w=240, h=50, cap=None):
        N[key] = d.add(Shape(p.el(kind, label), x, y, w, h, caption=cap))
        return N[key]

    def flow(a, b, label="", pts=None, label_xy=None):
        d.connect(p.rel("ControlFlow", N[a].el, N[b].el, label), N[a], N[b], points=pts, label_xy=label_xy)

    return d, N, node, flow


# H3.1 Bi-encoder: one shared encoder for the query and the passage ---------------
d, N, node, flow = activity("H3_1_bi_encoder")
node("q", "ActivityAction", "Câu hỏi (query)", 10, 40, 180)
node("p", "ActivityAction", "Đoạn văn (passage)", 10, 260, 180)
node("tq", "ActivityAction", "Tách token (câu hỏi)", 250, 40, 200)
node("tp", "ActivityAction", "Tách token (đoạn văn)", 250, 260, 200)
node("enc", "ActivityAction", "Transformer encoder dùng chung (self-attention + FFN)", 510, 140, 300, 70)
node("pq", "ActivityAction", "Pooling mean + L2 → e_q", 870, 40, 220)
node("pp", "ActivityAction", "Pooling mean + L2 → e_d", 870, 260, 220)
node("cos", "ActivityAction", "Cosine similarity(e_q, e_d)", 1150, 150, 230)
flow("q", "tq")
flow("p", "tp")
flow("tq", "enc", "mã hóa")
flow("tp", "enc", "mã hóa")
flow("enc", "pq")
flow("enc", "pp")
flow("pq", "cos")
flow("pp", "cos")

# H4.1 Five knowledge layers -------------------------------------------------------
d = p.diagram("H4_1_nam_lop_tri_thuc", "ClassDiagram")
layers = [
    "L4 Thủ tục: quy tắc trả lời, trích dẫn, từ chối | RAG service + prompt",
    "L3 Quan hệ: thực thể, quan hệ, đồ thị | Neo4j (KB1, KB2, KB), RAG đọc qua graph_search",
    "L2 Ngữ nghĩa: chunk + embedding 384 chiều | Qdrant + document_chunks",
    "L1 Cấu trúc: chương, điều, khoản, trang | section_path, document_sections",
    "L0 Bản gốc: PDF, hash, phiên bản | Filesystem + PostgreSQL",
]
L = [d.add(Shape(p.el("Class", t), 10, 10 + i * 100, 640, 50)) for i, t in enumerate(layers)]
for upper, lower in zip(L, L[1:]):
    d.connect(p.rel("Dependency", upper.el, lower.el), upper, lower)

# H4.2 Knowledge base build pipeline -------------------------------------------------
d, N, node, flow = activity("H4_2_pipeline_xay_kb")
stages = [("pdf", "PDF gốc (01_pages)"), ("ocr", "Parse + OCR (text + boxes)"),
          ("blk", "Phân tích block (02_nodes)"), ("tree", "Cây cấu trúc (03_structured)"),
          ("chk", "Adaptive chunk (04_chunks)"), ("meta", "Metadata (05_enriched)"),
          ("emb", "Embedding (06_embedded)"), ("qd", "Qdrant (points)")]
node("start", "InitialNode", "", 125, 10, 20, 20, cap=(155, 10, 10, 10))
for i, (k, t) in enumerate(stages):
    row, col = divmod(i, 4)
    x = 10 + (col if row == 0 else 3 - col) * 300
    node(k, "ActivityAction", t, x, 70 + row * 130, 250)
node("end", "ActivityFinalNode", "", 123, 330, 24, 24, cap=(153, 332, 10, 10))
flow("start", "pdf")
for (a, _), (b, _) in zip(stages, stages[1:]):
    flow(a, b)
flow("qd", "end")

# H4.4 Hybrid retrieval pipeline -----------------------------------------------------
d, N, node, flow = activity("H4_4_truy_xuat_lai")
rows = [
    [("emb", "Embedding câu hỏi (384 chiều)"), ("top", "Qdrant top-N (N = 300..1000)"),
     ("dedup", "Dedup (page, content)"), ("comb", "Combined: cos + 0.9·lex + 0.45·article")],
    [("ce", "Cross-encoder rerank top-10"), ("win", "Answer windows (1–4 câu, ≤ 800 ký tự)"),
     ("shape", "Shape gate (count/time/ratio/yesno/who/article)"), ("cov", "IDF + bigram weighted coverage")],
    [("wr", "Rerank cửa sổ"), ("sel", "Selection (intent limit + margin)"),
     ("llm", "LLM (Gemini/OpenAI) hoặc extractive fallback"), ("cit", "Citation (chunk_id, pages, section)")],
]
node("start", "InitialNode", "", 140, 10, 20, 20, cap=(170, 10, 10, 10))
order = []
for r, row in enumerate(rows):
    for c, (k, t) in enumerate(row):
        x = 10 + (c if r % 2 == 0 else 3 - c) * 320
        node(k, "ActivityAction", t, x, 70 + r * 130, 280, 56)
        order.append(k)
node("dec", "DecisionNode", "", 1080, 480, 40, 40, cap=(1130, 488, 10, 10))
node("ans", "ActivityAction", "Trả lời kèm trích dẫn", 900, 580, 220)
node("ref", "ActivityAction", "Từ chối: chưa đủ căn cứ", 1180, 580, 220)
node("end1", "ActivityFinalNode", "", 998, 680, 24, 24, cap=(1028, 682, 10, 10))
node("end2", "ActivityFinalNode", "", 1278, 680, 24, 24, cap=(1308, 682, 10, 10))
flow("start", "emb")
for a, b in zip(order, order[1:]):
    flow(a, b)
flow("cit", "dec")
flow("dec", "ans", "[đủ căn cứ]")
flow("dec", "ref", "[không đủ căn cứ]")
flow("ans", "end1")
flow("ref", "end2")

if __name__ == "__main__":
    Path(sys.argv[1]).write_text(p.xml(), encoding="utf-8")
    print("diagrams:", [x.name for x in p.diagrams])
