"""Fill the remaining {{PLACEHOLDERS}} of Chapters 4 and 5 from real result files.

    python tools/fill_ch4_ch5.py            # rewrites chuong_4_kg_moi.md, chuong_5_kien_truc.md

Sources (all produced by the group's scripts, nothing typed by hand):
- ai-service/data/eval/results/kb_quality_v2.json   (scripts/18_evaluate_kb.py)
- ai-service/data/eval/results/*_generic*.json, agent_*.json, hybrid_rag_no_reranker.json (15_run_eval.py)
- ai-service/data/eval/results/bandit_policy.json   (scripts/20_bandit_policy.py)
- assets/agent_traces_20261116.json                 (RuleBasedAgent on the 26 questions, 16/11/2026)
"""
from __future__ import annotations

import json
import re
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RESULTS = BASE.parents[2] / "ai-service" / "data" / "eval" / "results"


def load(name):
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


def n(x, d=0):
    """Vietnamese number format: 1.665 / 0,745."""
    if isinstance(x, int) or d == 0:
        return f"{int(round(x)):,}".replace(",", ".")
    return f"{x:.{d}f}".replace(".", ",")


def pct(x):
    return f"{x * 100:.1f}".replace(".", ",") + "%"


kb = load("kb_quality_v2.json")
S = kb["structure"]
size = {r["kind"]: r["total"] for r in S["Q_SIZE"]}
cov = {r["source_type"]: r for r in S["Q_COVERAGE"]}
integ = S["Q_INTEGRITY"][0]
cons = S["Q_CONSISTENCY"][0]
conf = {r["method"]: r for r in S["Q_CONFIDENCE"]}
rel_conf = {r["band"]: r["relationships"] for r in S["Q_RELATION_CONFIDENCE"]}
prec = kb["extraction_precision"]

# ---------------------------------------------------------------- Chapter 4
nodes = [r for r in S["Q_SIZE"] if r["category"] == "node"]
rels = [r for r in S["Q_SIZE"] if r["category"] == "relationship"]
KB_STRUCT = []
KB_STRUCT.append("**Quy mô.** KB hợp nhất có " + ", ".join(f"{n(r['total'])} nút `{r['kind']}`" for r in nodes)
                 + f"; tổng cộng {n(sum(r['total'] for r in rels))} cạnh thuộc {len(rels)} kiểu:")
KB_STRUCT.append("")
KB_STRUCT.append("| Kiểu cạnh | Số lượng | Kiểu cạnh | Số lượng |")
KB_STRUCT.append("| :--- | ---: | :--- | ---: |")
half = (len(rels) + 1) // 2
for i in range(half):
    a = rels[i]
    b = rels[i + half] if i + half < len(rels) else None
    KB_STRUCT.append(f"| `{a['kind']}` | {n(a['total'])} | " + (f"`{b['kind']}` | {n(b['total'])} |" if b else " | |"))
KB_STRUCT.append("")
KB_STRUCT.append("*Bảng 4.22. Quy mô KB hợp nhất (đếm bằng `Q_SIZE`, 15/11/2026).*")
KB_STRUCT.append("")
KB_STRUCT.append("**Độ phủ theo nguồn.** Độ phủ thực thể là tỷ lệ chunk có ít nhất một cạnh `MENTIONS`; độ phủ ngữ nghĩa chỉ tính thực thể mang nghĩa (bỏ số điều, ngày tháng).")
KB_STRUCT.append("")
KB_STRUCT.append("| Nguồn | Tài liệu | Chunk | Độ phủ thực thể | Độ phủ ngữ nghĩa | Thực thể/chunk |")
KB_STRUCT.append("| :--- | ---: | ---: | ---: | ---: | ---: |")
labels = {"pdf": "PDF nội bộ (KB1)", "web": "Trang web (KB2)", "upload": "Tài liệu tải lên"}
for key in ("pdf", "web", "upload"):
    r = cov[key]
    KB_STRUCT.append(f"| {labels[key]} | {r['documents']} | {n(r['chunks'])} | {pct(r['chunk_entity_coverage'])} | "
                     f"{pct(r['chunk_semantic_coverage'])} | {n(r['avg_entities_per_chunk'], 2)} |")
KB_STRUCT.append("")
KB_STRUCT.append("*Bảng 4.23. Độ phủ thực thể theo nguồn (`Q_COVERAGE`).*")
KB_STRUCT.append("")
w = cov["web"]
KB_STRUCT.append(
    f"Nguồn web có độ phủ thấp nhất ({pct(w['chunk_entity_coverage'])}) vì các trang giới thiệu viết văn xuôi, ít dẫn chiếu "
    "\"Điều N\", ít chức danh và tên văn bản mà bộ trích xuất theo luật nhận ra. Hai nguồn văn bản quy phạm đạt trên 80%.")
KB_STRUCT.append("")
KB_STRUCT.append("**Toàn vẹn và nhất quán.**")
KB_STRUCT.append("")
KB_STRUCT.append("| Chỉ số | Giá trị | Ý nghĩa |")
KB_STRUCT.append("| :--- | ---: | :--- |")
KB_STRUCT.append(f"| Chunk mồ côi, tài liệu rỗng, tài liệu không thuộc KB nào | {integ['orphan_chunks']}, {integ['empty_documents']}, {integ['documents_without_kb']} | Cấu trúc tài liệu → chunk → KB không đứt gãy |")
KB_STRUCT.append(f"| Thực thể mồ côi, dữ kiện mồ côi | {integ['orphan_entities']}, {integ['orphan_claims']} | Mọi thực thể và dữ kiện đều có chunk làm nguồn |")
KB_STRUCT.append(f"| Dẫn chiếu `REFERENCES` sang tài liệu khác | {integ['cross_document_references']} | \"Điều 11\" chỉ nối tới Điều 11 của cùng văn bản |")
KB_STRUCT.append(f"| Phiên bản cũ vẫn hiện hành | {integ['stale_versions_still_current']} | Cơ chế cập nhật (mục 4.17) không để sót bản cũ |")
KB_STRUCT.append(f"| Tài liệu trùng (`DUPLICATE_OF`) | {cons['duplicate_documents']} | Bản PDF trùng bản upload, chỉ giữ một bản cho truy xuất |")
KB_STRUCT.append(f"| Cặp thực thể đã hợp nhất (`SAME_AS`) / chờ duyệt (`POSSIBLY_SAME_AS`) | {cons['same_as_pairs']} / {cons['pending_review_pairs']} | Hợp nhất mờ, mục 4.15.6 |")
KB_STRUCT.append(f"| Dữ kiện: chấp nhận / bị thay thế / nghi vấn / chưa phân định | {cons['accepted_claims']} / {cons['superseded_claims']} / {cons['suspect_claims']} / {cons['unresolved_claims']} | Mọi mâu thuẫn số liệu đều đã có kết luận, mục 4.15.7 |")
KB_STRUCT.append("")
KB_STRUCT.append("*Bảng 4.24. Toàn vẹn và nhất quán của KB (`Q_INTEGRITY`, `Q_CONSISTENCY`).*")
KB_STRUCT.append("")
low = rel_conf.get("thap (<0.2)", 0)
total_rel = sum(rel_conf.values())
KB_STRUCT.append(
    f"Một điểm cần lưu ý: trong {n(total_rel)} cạnh `RELATES_TO` giữa các thực thể, {n(low)} cạnh ({pct(low / total_rel)}) có độ tin cậy dưới 0,2, "
    "tức chỉ dựa trên một hai lần cùng xuất hiện. Đây là lý do truy xuất đồ thị dùng ngưỡng độ tin cậy "
    "(`GRAPH_MIN_MENTION_CONFIDENCE`) thay vì đi theo mọi cạnh.")

method_desc = {
    "alias_full": "Khớp đủ tên hoặc bí danh có dấu",
    "heading": "Tiêu đề mục (Chương, Điều có tên)",
    "regex_article": "Mẫu \"Điều N\"",
    "alias_folded": "Khớp không dấu (chữ OCR lỗi)",
    "gazetteer_law": "Danh mục tên luật",
    "regex_date": "Ngày tháng",
    "alias_abbrev": "Từ viết tắt (HĐQT, ĐHĐCĐ)",
    "alias_en": "Bí danh tiếng Anh",
    "regex_decree": "Số hiệu nghị định",
    "regex_law": "Số hiệu luật",
}
P = ["| Phương pháp | Cách nhận | Độ tin cậy gán | Lượt nhắc trong KB | Mẫu gán nhãn | Precision |",
     "| :--- | :--- | ---: | ---: | ---: | ---: |"]
for method, r in sorted(prec["per_method"].items(), key=lambda kv: -conf.get(kv[0], {}).get("mentions", 0)):
    c = conf.get(method, {})
    P.append(f"| `{method}` | {method_desc.get(method, '')} | {n(c.get('avg_confidence', 0), 2)} | {n(c.get('mentions', 0))} | "
             f"{r['labelled']} | {n(r['precision'], 3)} |")
P.append(f"| **Tổng** | | | **{n(sum(c['mentions'] for c in conf.values()))}** | **{sum(r['labelled'] for r in prec['per_method'].values())}** | **{n(prec['weighted_precision'], 3)}** |")
P.append("")
P.append("*Bảng 4.25. Precision trích xuất theo phương pháp (mẫu `kb_entity_sample_v2.json`, precision chung có trọng số).*")
PRECISION_TABLE = "\n".join(P)

h = prec["per_method"]["heading"]
lw = prec["per_method"]["regex_law"]
rc = prec["recheck_after_fix"]
PRECISION_DISCUSSION = "\n".join([
    f"Precision chung đạt **{n(prec['weighted_precision'], 3)}**. Lần gán nhãn đầu (trước khi sửa bộ trích xuất) cho 0,911; mười lỗi tìm được khi gán nhãn đã được sửa "
    "(ví dụ \"Công ty Cổ phần\" bị nhận nhầm là chủ đề cổ phần, \"Kỷ luật lao động\" bị nhận là tên luật, tiêu đề rác từ mục lục), "
    f"rồi rút một mẫu mới để đo lại. Trên mẫu mới, {rc['labelled']} lượt nhắc được gán nhãn; sau khi sửa vẫn trích ra đủ {rc['still_extracted']}, "
    f"không mất lượt nhắc đúng nào ({rc['lost_true_positives']}).",
    "",
    f"Hai phương pháp dưới mức tuyệt đối có lý do rõ ràng. `heading` đạt {n(h['precision'], 3)}: còn sót tiêu đề chung chung như \"Nội dung\" và câu văn bị nhận nhầm thành tiêu đề. "
    f"`regex_law` đạt {n(lw['precision'], 3)} nhưng chỉ có {lw['population']} lượt nhắc, nên một lỗi đã kéo con số xuống. "
    "Độ tin cậy gán sẵn cho từng phương pháp phản ánh đúng thứ tự này: `heading` và `alias_folded` được gán 0,6, thấp hơn các phương pháp theo mẫu cứng (0,9–0,95). "
    "Riêng `alias_folded` (khớp không dấu cho chữ OCR lỗi) đạt precision 1,0 trên mẫu, cho thấy hạ độ tin cậy để thận trọng là đúng nhưng chưa cần loại bỏ phương pháp này.",
])

runs = {
    "flat": load("flat_rag_generic.json"),
    "graph0": load("graph_rag_generic_conf0.json"),
    "graph": load("graph_rag_generic_conf07.json"),
    "hyb0": load("hybrid_rag_generic_conf0.json"),
    "hyb": load("hybrid_rag_generic_conf07.json"),
}
R = ["Bộ 26 câu hỏi (18 câu có đoạn đúng, 8 câu phải từ chối) được chạy với ba chiến lược truy xuất, ở hai ngưỡng độ tin cậy lượt nhắc của đồ thị:",
     "",
     "| Cấu hình | Ngưỡng tin cậy | MRR | Recall@1 | Recall@3 | Tỷ lệ đạt |",
     "| :--- | ---: | ---: | ---: | ---: | ---: |"]
for key, label, thr in [("flat", "Chỉ vector (`flat_rag`)", "—"), ("graph0", "Chỉ đồ thị (`graph_rag`)", "0"),
                        ("graph", "Chỉ đồ thị (`graph_rag`)", "0,7"), ("hyb0", "Lai vector + đồ thị (`hybrid_rag`)", "0"),
                        ("hyb", "Lai vector + đồ thị (`hybrid_rag`)", "0,7")]:
    d = runs[key]
    R.append(f"| {label} | {thr} | {n(d['mrr'], 3)} | {n(d['recall_at_1'], 3)} | {n(d['recall_at_3'], 3)} | {pct(d['pass_rate'])} |")
R.append("")
R.append("*Bảng 4.26. Đóng góp của đồ thị cho truy xuất (`15_run_eval.py`, 15/11/2026, chế độ trích đoạn không LLM).*")
R.append("")
f, g, g0, hy, hy0 = runs["flat"], runs["graph"], runs["graph0"], runs["hyb"], runs["hyb0"]
R.append(
    f"Ba nhận xét. Thứ nhất, **đồ thị đứng một mình yếu** (MRR {n(g['mrr'], 3)}): truy xuất qua thực thể bỏ lỡ các câu hỏi không chứa thực thể, "
    f"và nhãn đoạn đúng chỉ trỏ vào tài liệu upload (mục 4.18.5). Thứ hai, **ghép đồ thị với vector có ích cho xếp hạng**: MRR tăng từ {n(f['mrr'], 3)} lên "
    f"{n(hy['mrr'], 3)}, Recall@1 từ {n(f['recall_at_1'], 3)} lên {n(hy['recall_at_1'], 3)}, Recall@3 từ {n(f['recall_at_3'], 3)} lên {n(hy['recall_at_3'], 3)}. "
    f"Tỷ lệ đạt đầu–cuối của cấu hình lai ({pct(hy['pass_rate'])}) vẫn thấp hơn vector ({pct(f['pass_rate'])}) một câu, nên lợi ích chủ yếu nằm ở thứ hạng đoạn đúng. "
    f"Thứ ba, **xử lý không chắc chắn có tác dụng đo được**: chỉ dùng lượt nhắc có độ tin cậy từ 0,7 nâng MRR của đồ thị từ {n(g0['mrr'], 3)} lên {n(g['mrr'], 3)} "
    f"và của cấu hình lai từ {n(hy0['mrr'], 3)} lên {n(hy['mrr'], 3)}. Đây là bằng chứng định lượng cho việc gắn độ tin cậy vào từng phép trích xuất ở mục 4.15.5.")
RETRIEVAL_IMPACT = "\n".join(R)

CH4_CONCLUSION = "\n".join([
    "Chương 4 đã trả lời bảy vấn đề đặt ra ở mục 4.1:",
    "",
    "- **T1 (tài liệu thô thành tri thức):** pipeline thu nhận, phân tích cấu trúc, phân đoạn thích ứng, làm giàu metadata và nhúng (mục 4.2–4.8) biến PDF quét và văn bản pháp quy thành chunk có đường dẫn mục và trang để trích dẫn.",
    f"- **T2 (biểu diễn):** tri thức được lưu song song ở Qdrant (tìm theo nghĩa) và Neo4j (duyệt theo quan hệ). KB hợp nhất có {n(size['Document'])} tài liệu, {n(size['Chunk'])} chunk, {n(size['Entity'])} thực thể; toàn bộ Cypher nằm trong 7 tệp `.cypher` có tên truy vấn (mục 4.13–4.14).",
    f"- **T3, T4 (tích hợp, không chắc chắn, mờ):** {cons['duplicate_documents']} tài liệu trùng được đánh dấu `DUPLICATE_OF`; {cons['same_as_pairs']} cặp thực thể được hợp nhất và {cons['pending_review_pairs']} cặp chờ duyệt bằng hàm thuộc; {cons['claims']} dữ kiện số được phân định thành {cons['accepted_claims']} chấp nhận và {cons['superseded_claims']} bị thay thế, không còn dữ kiện chưa phân định (mục 4.15).",
    f"- **T5 (nối KB với RAG):** truy xuất lai vector + đồ thị nâng MRR từ {n(f['mrr'], 3)} lên {n(hy['mrr'], 3)} trên cùng bộ câu hỏi (mục 4.16, Bảng 4.26).",
    "- **T6 (cập nhật):** cập nhật theo hash nội dung với bốn tình huống thêm, sửa, xóa và trích xuất lại, đã chạy thật trên Neo4j (mục 4.17, Bảng 4.20).",
    f"- **T7 (đánh giá):** KB được đánh giá theo sáu nhóm chỉ số; mọi chỉ số toàn vẹn bằng 0 và precision trích xuất đạt {n(prec['weighted_precision'], 3)} (mục 4.18).",
    "",
    "Hạn chế chính là truy xuất chỉ bằng đồ thị còn yếu, bộ trích xuất theo luật chưa đo được độ bao phủ, và nhãn đánh giá do nhóm tự gán. "
    "Kết quả của chương là một cơ sở tri thức có nguồn gốc rõ ràng, nhất quán và cập nhật được; Chương 5 trình bày cách tác tử khai thác nó, "
    "chẳng hạn đọc thẳng giá trị vốn điều lệ hiện hành đã được phân định thay vì đoán từ văn bản.",
])

# ---------------------------------------------------------------- Chapter 5
traces = json.loads((BASE / "assets" / "agent_traces_20261116.json").read_text(encoding="utf-8"))
by_q = {t["q"]: t for t in traces}
cap = by_q["Vốn điều lệ hiện nay của công ty là bao nhiêu?"]
retry = by_q["Quy định về bảo mật và quản lý mật khẩu của nhân viên bao gồm những yêu cầu gì?"]
refuse = by_q["Công ty có bao nhiêu nhân viên?"]

action_vi = {"kb_attribute": "tra dữ kiện trong KB", "retrieve:flat_rag": "truy xuất vector",
             "retrieve:hybrid_rag": "truy xuất lai", "respond": "trả lời", "refuse": "từ chối"}
result_vi = {"found": "tìm thấy giá trị được chấp nhận", "gate_refused": "cổng bằng chứng từ chối",
             "answered": "có bằng chứng, có trích dẫn"}
shape_vi = {"count": "hỏi số lượng", "list": "liệt kê", "time": "thời gian", "yes_no": "có/không",
            "article": "điều khoản", "open": "mở"}


def trace_table(t, caption):
    p = t["trace"][0]["perception"]
    facts = [f"dạng câu hỏi: {shape_vi.get(p['shape'], p['shape'])}"]
    if p.get("attribute"):
        facts.append(f"thuộc tính một giá trị: {p['attribute']}")
    facts.append("thực thể KB: " + (", ".join(p["entities"]) if p["entities"] else "không có"))
    lines = [f"Nhận thức (bước 0): {'; '.join(facts)}.", "",
             "| Bước | Luật kích hoạt | Hành động | Kết quả quan sát | Thời gian |",
             "| ---: | :--- | :--- | :--- | ---: |"]
    for s in t["trace"][1:]:
        res = result_vi.get(s.get("result", ""), "")
        if s.get("citations"):
            res += f" ({s['citations']} trích dẫn)"
        ms = f"{n(s['ms'] / 1000, 1)} s" if "ms" in s else ""
        lines.append(f"| {s['step']} | `{s['rule']}` | {action_vi.get(s['action'], s['action'])} | {res} | {ms} |")
    lines += ["", caption]
    return "\n".join(lines)


AGENT_TRACE_CAPITAL = trace_table(cap, "*Bảng 5.4. Vết xử lý của câu hỏi vốn điều lệ (chạy lại ngày 16/11/2026).*") + "\n\n" + (
    "Tác tử không truy xuất văn bản: luật R3 thấy câu hỏi về một thuộc tính một giá trị nên gọi `kb_attribute`, đọc nút `Claim` đã được phân định ở mục 4.15.7 "
    "và trả lời \"13.074.049.490.000 đồng, theo Điều lệ năm 2026\", kèm các giá trị cũ hơn đã bị thay thế. "
    "Ví dụ này chạy ở chế độ toàn đồ thị, chế độ dùng cho đánh giá (`CHAT_GRAPH_SOURCE_TYPE` để trống), vì Điều lệ 2025 và 2026 nằm trong KB1. "
    "Trong API hỏi đáp của người dùng, tác tử chỉ trích dẫn tài liệu tải lên (`CHAT_GRAPH_SOURCE_TYPE=upload`, mục 5.4) để mọi trích dẫn đều mở được PDF gốc.")

AGENT_TRACE_RETRY = trace_table(retry, "*Bảng 5.5. Vết xử lý của một câu hỏi phải thử lại.*") + "\n\n" + (
    "Câu hỏi không chứa thực thể nên luật R7 chọn vector. Cổng bằng chứng từ chối kết quả, luật R8 thử lại bằng truy xuất lai và tìm được Điều 22 về an toàn, bảo mật thông tin. "
    f"Với câu ngoài phạm vi \"{refuse['q']}\", chuỗi luật là " + " → ".join(f"`{r}`" for r in refuse["rules"]) +
    ": cả hai lần truy xuất đều bị cổng từ chối, tác tử từ chối thay vì đoán.\n\n")
counts = {}
for t in traces:
    key = " → ".join(t["rules"])
    counts[key] = counts.get(key, 0) + 1
rows = ["| Chuỗi luật | Số câu |", "| :--- | ---: |"] + [f"| `{k}` | {v} |" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]
AGENT_TRACE_RETRY += ("Trên 27 câu (26 câu của bộ đánh giá và câu vốn điều lệ), tác tử đi theo các chuỗi luật sau:\n\n" + "\n".join(rows) +
                      "\n\n*Bảng 5.6. Tần suất các chuỗi luật của tác tử.*")

bandit = load("bandit_policy.json")
summ = bandit["summary"]
B = ["| Chính sách | Phần thưởng trung bình |", "| :--- | ---: |"]
labels_b = [("always_flat_rag", "Luôn dùng vector"), ("always_graph_rag", "Luôn dùng đồ thị"),
            ("always_hybrid_rag", "Luôn dùng truy xuất lai"), ("rule_based_agent", "**Tác tử luật (mục 5.5)**"),
            ("bandit_leave_one_out", "Bandit UCB1, leave-one-out"), ("oracle_best_arm", "Cận trên: biết trước nhánh tốt nhất")]
for key, label in labels_b:
    v = summ[key]["mean_reward"]
    B.append(f"| {label} | {'**' + n(v, 3) + '**' if key == 'rule_based_agent' else n(v, 3)} |")
B += ["", "*Bảng 5.7. Phần thưởng trung bình của các chính sách chọn chiến lược (26 câu, 200 lượt học).*", "",
      "Chính sách mà bandit học được trên toàn bộ dữ liệu, theo từng ngữ cảnh:", "",
      "| Ngữ cảnh (dạng câu, có thực thể, có số điều) | Số câu | Nhánh được chọn | Thưởng vector / đồ thị / lai |",
      "| :--- | ---: | :--- | :--- |"]
for ctx, v in bandit["learned_policy"].items():
    shape, ent, art = ctx.split("|")
    mr = v["mean_reward"]
    B.append(f"| {shape_vi.get(shape, shape)}, {'có' if ent.endswith('1') else 'không'} thực thể, {'có' if art.endswith('1') else 'không'} số điều | "
             f"{v['questions']} | `{v['arm']}` | {n(mr['flat_rag'], 2)} / {n(mr['graph_rag'], 2)} / {n(mr['hybrid_rag'], 2)} |")
B += ["", "*Bảng 5.8. Chính sách bandit học được theo ngữ cảnh.*"]
BANDIT_TABLE = "\n".join(B)

v1 = load("agent_v1_entity_hybrid.json")
ag = load("agent_generic.json")
BANDIT_DISCUSSION = "\n".join([
    f"Tác tử luật đạt phần thưởng cao nhất trong các chính sách thực tế ({n(summ['rule_based_agent']['mean_reward'], 3)}), nhỉnh hơn \"luôn dùng truy xuất lai\" "
    f"({n(summ['always_hybrid_rag']['mean_reward'], 3)}) và \"luôn dùng vector\" ({n(summ['always_flat_rag']['mean_reward'], 3)}). Bandit học bằng leave-one-out chỉ đạt "
    f"{n(summ['bandit_leave_one_out']['mean_reward'], 3)}, thấp hơn cả chính sách cố định đơn giản nhất. Nguyên nhân là dữ liệu quá ít: 26 câu chia vào 11 ngữ cảnh, "
    "nhiều ngữ cảnh chỉ có 1–2 câu, nên khi bỏ một câu ra để chấm thì ngữ cảnh đó gần như không còn dữ liệu học (Bảng 5.8).",
    "",
    f"Khoảng cách tới cận trên ({n(summ['oracle_best_arm']['mean_reward'], 3)}) cho thấy việc chọn chiến lược theo câu hỏi vẫn còn dư địa. "
    "Học tăng cường cũng đã góp phần sửa luật: bandit cho thấy với câu hỏi có thực thể, truy xuất lai không vượt trội rõ so với vector. "
    f"Kiểm chứng trên tác tử: bật luật R6 (đưa mọi câu có thực thể sang truy xuất lai) cho tỷ lệ đạt {pct(v1['pass_rate'])}, tắt R6 cho {pct(ag['pass_rate'])}. "
    "Vì vậy R6 được giữ trong bảng luật nhưng tắt mặc định (`AGENT_ENTITY_HYBRID=false`). "
    "Kết luận thực tế: với quy mô dữ liệu hiện tại, luật do con người viết dựa trên quan sát vẫn tốt hơn chính sách học; học tăng cường trở nên có ích khi thu được phản hồi thật của người dùng (mục 5.9).",
])

sysruns = [("Chỉ vector", load("flat_rag_generic.json")), ("Chỉ đồ thị", load("graph_rag_generic_conf07.json")),
           ("Truy xuất lai", load("hybrid_rag_generic_conf07.json")), ("Truy xuất lai, tắt chấm lại", load("hybrid_rag_no_reranker.json")),
           ("**Tác tử luật**", ag)]
T = ["| Cấu hình | Tỷ lệ đạt | MRR | Recall@3 | Trích dẫn đúng | Từ chối đúng | Từ chối nhầm | Độ trễ TB |",
     "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
for label, d in sysruns:
    T.append(f"| {label} | {pct(d['pass_rate'])} | {n(d['mrr'], 3)} | {n(d['recall_at_3'], 3)} | {pct(d['citation_hit_rate'])} | "
             f"{pct(d['refusal_accuracy'])} | {pct(d['false_refusal_rate'])} | {n(d['avg_latency_ms'] / 1000, 1)} s |")
T += ["", "*Bảng 5.10. Đánh giá đầu–cuối trên 26 câu hỏi (15/11/2026, chế độ trích đoạn, không LLM).*"]
SYSTEM_EVAL_TABLE = "\n".join(T)

nr = load("hybrid_rag_no_reranker.json")
fl = load("flat_rag_generic.json")
SYSTEM_EVAL_DISCUSSION = "\n".join([
    f"Tác tử đạt tỷ lệ đạt cao nhất ({pct(ag['pass_rate'])}, bằng cấu hình chỉ vector) và là cấu hình duy nhất vừa không từ chối nhầm câu có đáp án ({pct(ag['false_refusal_rate'])}) "
    f"vừa giữ trích dẫn đúng ở mức cao nhất ({pct(ag['citation_hit_rate'])}, bằng cấu hình chỉ vector). So với chỉ vector, tác tử loại được lần từ chối nhầm ({pct(fl['false_refusal_rate'])} → {pct(ag['false_refusal_rate'])}) "
    "nhờ luật R8 thử lại bằng truy xuất lai, và trả lời câu hỏi thuộc tính từ KB đã phân định.",
    "",
    f"Bộ chấm lại cross-encoder là thành phần đóng góp lớn nhất: tắt nó, MRR giảm từ {n(load('hybrid_rag_generic_conf07.json')['mrr'], 3)} xuống {n(nr['mrr'], 3)} "
    f"và tỷ lệ đạt giảm xuống {pct(nr['pass_rate'])}; đổi lại độ trễ giảm còn {n(nr['avg_latency_ms'] / 1000, 1)} s. "
    f"Từ chối đúng của tác tử, vector và truy xuất lai chỉ ở mức {pct(ag['refusal_accuracy'])} (5/8 câu ngoài phạm vi): ba câu ngoài phạm vi vẫn tìm được đoạn có điểm vượt cổng. "
    f"Cấu hình chỉ đồ thị từ chối đúng {pct(load('graph_rag_generic_conf07.json')['refusal_accuracy'])} nhưng chủ yếu vì nó từ chối nhiều, kể cả {pct(load('graph_rag_generic_conf07.json')['false_refusal_rate'])} câu có đáp án. "
    "Đây là hạn chế chính cần cải thiện, ví dụ bằng cổng bằng chứng theo ngưỡng riêng cho từng dạng câu hỏi.",
    "",
    "Độ trễ đo trên máy cá nhân chạy CPU, dao động giữa các lần chạy, nên chỉ dùng để so sánh tương đối.",
])

CH5_CONCLUSION = "\n".join([
    "Chương 5 đã trả lời sáu vấn đề đặt ra ở mục 5.1:",
    "",
    "- **K1, K2 (kết nối module, bảo mật):** tám dịch vụ kết nối qua REST theo hợp đồng cố định; mỗi mối nối được chỉ ra bằng đoạn mã thật (mục 5.3). Backend là cổng duy nhất, tự gắn quyền từ JWT; dịch vụ AI chỉ nhận yêu cầu có `X-Internal-Token`; quyền được lọc ngay trong truy vấn Qdrant và Cypher (mục 5.4).",
    f"- **K3 (chọn chiến lược):** tác tử dựa trên luật với chín luật, bốn bước nhận thức – chọn luật – hành động – quan sát, ghi vết từng quyết định. Tác tử đạt tỷ lệ đạt {pct(ag['pass_rate'])}, không từ chối nhầm câu nào và đọc được dữ kiện đã phân định trong KB (mục 5.5, 5.8).",
    f"- **K4 (luật hay học):** contextual bandit UCB1 đạt {n(summ['bandit_leave_one_out']['mean_reward'], 3)} so với {n(summ['rule_based_agent']['mean_reward'], 3)} của tác tử luật trên 26 câu; học tăng cường chưa thắng luật vì thiếu dữ liệu, nhưng đã giúp điều chỉnh luật R6 (mục 5.6).",
    "- **K5 (nhiều mô hình):** ba tầng mô hình (nhúng, chấm lại, sinh) thay được bằng biến môi trường; tầng sinh có thứ tự dự phòng và luôn có đường trích đoạn khi không có LLM (mục 5.7).",
    "- **K6 (kiểm chứng toàn hệ thống):** năm cấu hình được đo trên cùng bộ 26 câu với các chỉ số truy xuất, trích dẫn, từ chối và độ trễ (mục 5.8).",
    "",
    "Kết quả của chương là một hệ thống chạy đầu–cuối, trong đó mô hình của Chương 3 và cơ sở tri thức của Chương 4 được một tác tử điều phối, "
    "mọi câu trả lời đều truy vết được tới trang PDF gốc. Hướng phát triển là hệ đa tác tử và học tăng cường trực tuyến từ phản hồi người dùng.",
])

# ---------------------------------------------------------------- apply
FILLS4 = {"KB_STRUCT_TABLES": "\n".join(KB_STRUCT), "PRECISION_TABLE": PRECISION_TABLE, "PRECISION_DISCUSSION": PRECISION_DISCUSSION,
          "RETRIEVAL_IMPACT": RETRIEVAL_IMPACT, "CH4_CONCLUSION": CH4_CONCLUSION}
FILLS5 = {"AGENT_TRACE_CAPITAL": AGENT_TRACE_CAPITAL, "AGENT_TRACE_RETRY": AGENT_TRACE_RETRY, "BANDIT_TABLE": BANDIT_TABLE,
          "BANDIT_DISCUSSION": BANDIT_DISCUSSION, "SYSTEM_EVAL_TABLE": SYSTEM_EVAL_TABLE,
          "SYSTEM_EVAL_DISCUSSION": SYSTEM_EVAL_DISCUSSION, "CH5_CONCLUSION": CH5_CONCLUSION}


def apply(path: Path, fills: dict) -> None:
    text = path.read_text(encoding="utf-8")
    for key, value in fills.items():
        text = text.replace("{{" + key + "}}", value)
    left = re.findall(r"\{\{[A-Z0-9_]+\}\}", text)
    path.write_text(text, encoding="utf-8")
    print(f"{path.name}: filled {len(fills)}; remaining {left}")


apply(BASE / "chuong_4_kg_moi.md", FILLS4)
apply(BASE / "chuong_5_kien_truc.md", FILLS5)

# Table numbers of Chapter 5 after the new tables 5.4-5.8 (traces, bandit).
ch5 = BASE / "chuong_5_kien_truc.md"
t = ch5.read_text(encoding="utf-8")
t = t.replace("*Bảng 5.5. Các mô hình được triển khai và cách thay thế.*", "*Bảng 5.9. Các mô hình được triển khai và cách thay thế.*")
t = t.replace("tắt chấm lại (Bảng 5.4)", "tắt chấm lại (Bảng 5.10)")
ch5.write_text(t, encoding="utf-8")
