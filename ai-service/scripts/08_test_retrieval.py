import sys
import io
import time

from app.retriever import VectorRetriever

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def main():
    print("🔎 Đang khởi tạo VectorRetriever...")
    retriever = VectorRetriever()

    test_queries = [
        "Chủ tịch Hội đồng Quản trị có quyền và nghĩa vụ gì?",
        "Thời hạn hoạt động của Công ty là bao lâu?",
        "Ai là người đại diện theo pháp luật của Công ty?",
        "Vốn điều lệ của công ty"
    ]

    for q_idx, query in enumerate(test_queries, 1):
        print("\n" + "=" * 70)
        print(f"❓ CÂU HỎI {q_idx}: \"{query}\"")
        print("=" * 70)

        start = time.time()
        results = retriever.search(query, top_k=2)
        elapsed = (time.time() - start) * 1000

        print(f"⏱️ Thời gian truy vấn: {elapsed:.1f}ms | Tìm thấy: {len(results)} kết quả phù hợp nhất\n")

        for r_idx, hit in enumerate(results, 1):
            score = hit["score"]
            chunk_id = hit["chunk_id"]
            meta = hit["metadata"]
            p_start = meta.get("page_start", "?")
            p_end = meta.get("page_end", "?")
            p_str = f"Trang {p_start}" if p_start == p_end else f"Trang {p_start} → {p_end}"
            path_str = " > ".join(meta.get("section_path", [])) or "*(Mở đầu)*"

            content_snippet = hit["content"].replace("\n", " ")
            if len(content_snippet) > 180:
                content_snippet = content_snippet[:180] + "..."

            print(f"  [{r_idx}] ĐIỂM TƯƠNG ĐỒNG: {score:.4f} | ID: {chunk_id}")
            print(f"      📄 Vị trí: {p_str} | Phả hệ: {path_str}")
            print(f"      💬 Nội dung: \"{content_snippet}\"")
            print()

if __name__ == "__main__":
    main()
