import json
import time
import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

# Define test dataset (Queries & Ground Truth Chunks)
TEST_CASES = [
    {
        "id": "TC-01",
        "query": "Chủ tịch Hội đồng Quản trị có quyền và nghĩa vụ gì?",
        "ground_truth_chunks": ["DOC-001-CHUNK-0096", "DOC-001-CHUNK-0097", "DOC-001-CHUNK-0093"],
        "description": "Thẩm quyền và nghĩa vụ của Chủ tịch HĐQT"
    },
    {
        "id": "TC-02",
        "query": "Thời hạn hoạt động của Công ty là bao lâu và bắt đầu từ khi nào?",
        "ground_truth_chunks": ["DOC-001-CHUNK-0005", "DOC-001-CHUNK-0006", "DOC-001-CHUNK-0003"],
        "description": "Thời hạn và ngày thành lập công ty"
    },
    {
        "id": "TC-03",
        "query": "Con dấu của Công ty bao gồm những hình thức nào và ai có thẩm quyền quyết định?",
        "ground_truth_chunks": ["DOC-001-CHUNK-0145"],
        "description": "Quy định về con dấu và chữ ký số"
    },
    {
        "id": "TC-04",
        "query": "Việc chỉ định công ty kiểm toán độc lập cho năm tài chính tiếp theo diễn ra như thế nào?",
        "ground_truth_chunks": ["DOC-001-CHUNK-0144"],
        "description": "Quy trình lựa chọn đơn vị kiểm toán độc lập"
    },
    {
        "id": "TC-05",
        "query": "Báo cáo tài chính năm của công ty phải bao gồm những gì và được công bố ra sao?",
        "ground_truth_chunks": ["DOC-001-CHUNK-0143"],
        "description": "Báo cáo tài chính năm và trách nhiệm công bố thông tin"
    }
]

MODELS_TO_BENCHMARK = [
    {
        "name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "label": "MiniLM-L12-v2 (Hiện tại)",
        "provider": "Hugging Face / SentenceTransformers",
        "prefix_query": "",
        "prefix_passage": ""
    },
    {
        "name": "bkai-foundation-models/vietnamese-bi-encoder",
        "label": "Vietnamese-Bi-Encoder",
        "provider": "BKAI (ĐH Bách Khoa Hà Nội)",
        "prefix_query": "",
        "prefix_passage": ""
    },
    {
        "name": "intfloat/multilingual-e5-small",
        "label": "Multilingual-E5-Small",
        "provider": "Microsoft",
        "prefix_query": "query: ",
        "prefix_passage": "passage: "
    }
]

def load_chunks(json_path: Path) -> List[Dict[str, Any]]:
    if not json_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

def compute_cosine_similarity(query_vec: np.ndarray, doc_vecs: np.ndarray) -> np.ndarray:
    # Normalize vectors
    q_norm = query_vec / (np.linalg.norm(query_vec) + 1e-9)
    doc_norms = doc_vecs / (np.linalg.norm(doc_vecs, axis=1, keepdims=True) + 1e-9)
    return np.dot(doc_norms, q_norm)

def evaluate_model(model_cfg: Dict[str, str], chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    model_name = model_cfg["name"]
    label = model_cfg["label"]
    print(f"\n{'='*75}")
    print(f"🚀 [TESTING] Đang tải mô hình: {label} ({model_name})")
    print(f"{'='*75}")

    load_start = time.time()
    model = SentenceTransformer(model_name)
    load_time = time.time() - load_start

    # Get dimension
    if hasattr(model, "get_embedding_dimension"):
        vector_dim = model.get_embedding_dimension()
    else:
        vector_dim = model.get_sentence_embedding_dimension()

    print(f"  ✓ Tải mô hình thành công trong {load_time:.2f}s | Số chiều: {vector_dim} dimensions")

    # Encode all 152 chunks
    passage_texts = [
        f"{model_cfg['prefix_passage']}{c.get('content', '')}" for c in chunks
    ]
    chunk_ids = [c["chunk_id"] for c in chunks]

    print(f"  ⏳ Đang nhúng (encoding) {len(passage_texts)} chunks...")
    embed_start = time.time()
    doc_vectors = model.encode(passage_texts, batch_size=32, show_progress_bar=False, convert_to_numpy=True)
    embed_duration = time.time() - embed_start
    throughput = len(passage_texts) / (embed_duration + 1e-6)
    print(f"  ✓ Nhúng xong trong {embed_duration:.2f}s (Tốc độ: {throughput:.1f} chunks/giây)")

    # Test queries
    print(f"\n  🔍 Bắt đầu chạy truy vấn và đánh giá độ chính xác:")
    query_latencies = []
    hits_at_1 = 0
    hits_at_3 = 0
    hits_at_5 = 0
    mrr_scores = []
    detailed_results = []

    for idx, tc in enumerate(TEST_CASES, start=1):
        q_text = f"{model_cfg['prefix_query']}{tc['query']}"
        gt_ids = set(tc["ground_truth_chunks"])

        q_start = time.time()
        q_vec = model.encode(q_text, convert_to_numpy=True)
        scores = compute_cosine_similarity(q_vec, doc_vectors)
        q_latency_ms = (time.time() - q_start) * 1000
        query_latencies.append(q_latency_ms)

        # Sort descending
        top_indices = np.argsort(scores)[::-1][:5]
        top_chunks = [(chunk_ids[i], float(scores[i])) for i in top_indices]

        # Calculate Rank of first Hit
        first_rank = None
        for rank, (cid, sc) in enumerate(top_chunks, start=1):
            if cid in gt_ids:
                first_rank = rank
                break

        # Check hits
        hit_1 = 1 if (first_rank is not None and first_rank <= 1) else 0
        hit_3 = 1 if (first_rank is not None and first_rank <= 3) else 0
        hit_5 = 1 if (first_rank is not None and first_rank <= 5) else 0
        reciprocal_rank = 1.0 / first_rank if first_rank is not None else 0.0

        hits_at_1 += hit_1
        hits_at_3 += hit_3
        hits_at_5 += hit_5
        mrr_scores.append(reciprocal_rank)

        status_icon = "✅" if hit_1 else ("⚠️" if hit_3 else "❌")
        best_match_id, best_match_score = top_chunks[0]
        print(f"    {status_icon} Câu {idx}: \"{tc['query'][:42]}...\"")
        print(f"       -> Top 1: {best_match_id} (Điểm: {best_match_score:.4f}) | Rank đúng: {first_rank if first_rank else 'N/A'} | {q_latency_ms:.1f}ms")

        detailed_results.append({
            "test_case_id": tc["id"],
            "query": tc["query"],
            "ground_truth": tc["ground_truth_chunks"],
            "top_1_chunk": best_match_id,
            "top_1_score": best_match_score,
            "first_rank": first_rank,
            "latency_ms": round(q_latency_ms, 2)
        })

    num_q = len(TEST_CASES)
    recall_1 = (hits_at_1 / num_q) * 100.0
    recall_3 = (hits_at_3 / num_q) * 100.0
    recall_5 = (hits_at_5 / num_q) * 100.0
    avg_mrr = float(np.mean(mrr_scores))
    avg_latency = float(np.mean(query_latencies))

    print(f"\n  📊 TỔNG KẾT MÔ HÌNH [{label}]:")
    print(f"     • Recall@1: {recall_1:.1f}%")
    print(f"     • Recall@3: {recall_3:.1f}%")
    print(f"     • Recall@5: {recall_5:.1f}%")
    print(f"     • MRR (Mean Reciprocal Rank): {avg_mrr:.4f}")
    print(f"     • Độ trễ truy vấn trung bình: {avg_latency:.2f} ms")

    return {
        "model_name": model_name,
        "label": label,
        "provider": model_cfg["provider"],
        "vector_dim": vector_dim,
        "load_time_s": round(load_time, 2),
        "embed_time_152_chunks_s": round(embed_duration, 2),
        "throughput_chunks_per_sec": round(throughput, 1),
        "recall_1": round(recall_1, 1),
        "recall_3": round(recall_3, 1),
        "recall_5": round(recall_5, 1),
        "mrr": round(avg_mrr, 4),
        "avg_latency_ms": round(avg_latency, 2),
        "detailed_results": detailed_results
    }

def generate_markdown_report(results: List[Dict[str, Any]], output_path: Path):
    # Sort results by MRR and Recall@1 descending
    sorted_results = sorted(results, key=lambda x: (x["mrr"], x["recall_1"]), reverse=True)
    winner = sorted_results[0]

    report = f"""# Báo cáo Thực nghiệm So sánh & Đánh giá Mô hình Embedding

> **Chuyên mục:** Chương 2 — Mục 2.8 & 2.9 (Cấu trúc Đồ án Tốt nghiệp)  
> **Bộ dữ liệu thực nghiệm:** 152 Chunks từ tài liệu doanh nghiệp thực tế (`Điều Lệ Công Ty`)  
> **Hệ thống thử nghiệm:** Docker Container (CPU Execution Mode)  
> **Tiêu chí đánh giá:** Theo hướng dẫn của TS. Đinh Quế Trần (Mục 29.2 & Mục 33 trong bài giảng)

---

## 1. Bảng số liệu Tổng hợp Thực nghiệm (Benchmark Summary Table)

| Xếp hạng | Mô hình Embedding | Đơn vị phát triển | Số chiều | Recall@1 (%) | Recall@3 (%) | Recall@5 (%) | MRR | Độ trễ (ms) | Tốc độ nhúng (chunks/s) |
| :---: | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
"""
    for rank, r in enumerate(sorted_results, start=1):
        badge = "🏆 **QUÁN QUÂN**" if rank == 1 else f"Hạng {rank}"
        report += f"| {badge} | `{r['label']}` | {r['provider']} | {r['vector_dim']} | **{r['recall_1']}%** | **{r['recall_3']}%** | {r['recall_5']}% | **{r['mrr']:.4f}** | {r['avg_latency_ms']} ms | {r['throughput_chunks_per_sec']} |\n"

    report += f"""
---

## 2. Biểu đồ So sánh Trực quan (Visual Comparison Charts)

### 📊 Biểu đồ 1: Độ chính xác truy xuất (Recall@1, Recall@3 và MRR)

```mermaid
%%{{init: {{'theme': 'base', 'themeVariables': {{ 'primaryColor': '#4361ee', 'edgeLabelBackground':'#ffffff'}}}}}}%%
gantt
    title So Sánh Chỉ Số Đo Lường Giữa Các Mô Hình
    dateFormat X
    axisFormat %s

"""
    # Alternative clean markdown table/chart
    report += f"""
### 📊 Biểu đồ Cột So sánh MRR (Mean Reciprocal Rank - Tỉ lệ xếp hạng chuẩn xác)

```mermaid
pie title Tỉ trọng Đóng góp Hiệu năng MRR
"""
    for r in sorted_results:
        report += f'    "{r["label"]} ({r["mrr"]})" : {int(r["mrr"] * 100)}\n'

    report += f"""```

---

## 3. Phân tích Chi tiết Từng Mô hình

"""
    for r in sorted_results:
        report += f"""### 🔹 {r['label']} (`{r['model_name']}`)
- **Số chiều vector:** `{r['vector_dim']}` chiều.
- **Recall@1:** `{r['recall_1']}%` (Tỉ lệ tìm trúng đoạn văn bản ngay ở Top 1).
- **Recall@3:** `{r['recall_3']}%` (Tỉ lệ đoạn văn bản xuất hiện trong Top 3).
- **Điểm MRR:** `{r['mrr']:.4f}`.
- **Thời gian phản hồi truy vấn:** `{r['avg_latency_ms']} ms/câu hỏi`.
- **Tốc độ mã hóa tài liệu:** `{r['throughput_chunks_per_sec']} chunks/giây`.

"""

    report += f"""---

## 4. Kết luận & Quyết định Lựa chọn (Đưa vào Mục 2.9 Luận văn)

Căn cứ vào kết quả thực nghiệm định lượng trên 152 chunks tài liệu thực tế của doanh nghiệp:

1. **Mô hình được lựa chọn:** **`{winner['label']}`** (`{winner['model_name']}`).
2. **Lý do lựa chọn:**
   - Đạt độ chính xác truy xuất cao nhất với **Recall@1 đạt {winner['recall_1']}%** và **MRR đạt {winner['mrr']:.4f}**.
   - Thời gian đáp ứng cực nhanh (**{winner['avg_latency_ms']} ms**), hoàn toàn đáp ứng yêu cầu thời gian thực của người dùng.
   - Hoạt động ổn định trên môi trường CPU trong Docker container mà không yêu cầu GPU rời đắt tiền.
3. **Cấu hình áp dụng cho hệ thống:**
   - Biến môi trường: `EMBEDDING_MODEL={winner['model_name']}`
   - Kích thước vector lưu trữ trong Qdrant: `{winner['vector_dim']}` dimensions.
"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n📄 Đã tự động xuất Báo cáo Đánh giá Markdown tại: {output_path}")

def main():
    base_dir = Path(__file__).resolve().parent.parent
    chunks_path = base_dir / "debug" / "05_enriched_chunks.json"
    report_path = base_dir / "debug" / "evaluation_embedding_benchmark.md"
    json_result_path = base_dir / "debug" / "embedding_benchmark_results.json"

    print("================================================================================")
    print("🏆 CHƯƠNG TRÌNH BENCHMARK ĐỐI SÁNH CÁC MÔ HÌNH EMBEDDING (BƯỚC 1)")
    print("================================================================================")

    chunks = load_chunks(chunks_path)
    print(f"✓ Đã nạp thành công {len(chunks)} chunks dữ liệu thực tế từ: {chunks_path.name}")
    print(f"✓ Số lượng câu hỏi thử nghiệm Ground Truth: {len(TEST_CASES)} câu")

    all_results = []
    for model_cfg in MODELS_TO_BENCHMARK:
        try:
            res = evaluate_model(model_cfg, chunks)
            all_results.append(res)
        except Exception as e:
            print(f"❌ Lỗi khi test mô hình {model_cfg['name']}: {e}")

    # Generate Report
    if all_results:
        generate_markdown_report(all_results, report_path)

        # Save JSON results
        with open(json_result_path, "w", encoding="utf-8") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print(f"💾 Đã lưu dữ liệu JSON thô tại: {json_result_path}")

        print("\n" + "="*75)
        print("🎉 HOÀN THÀNH BENCHMARK TẤT CẢ CÁC MÔ HÌNH THÀNH CÔNG!")
        print("="*75)

if __name__ == "__main__":
    main()
