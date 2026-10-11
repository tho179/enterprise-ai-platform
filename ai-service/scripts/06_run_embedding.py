import sys
import io
import json
import time
from pathlib import Path

from app.embedding_service import EmbeddingService

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def main():
    in_path = Path("debug/05_enriched_chunks.json")
    if not in_path.exists():
        print(f"❌ Không tìm thấy file {in_path}. Vui lòng chạy pipeline M2 trước.")
        return

    print(f"📂 Đang đọc dữ liệu chunks từ: {in_path.name}")
    chunks = json.loads(in_path.read_text(encoding="utf-8"))
    print(f"   -> Tìm thấy {len(chunks)} chunks.")

    print("\n🧠 Đang khởi tạo EmbeddingService và tải mô hình...")
    start_init = time.time()
    embedder = EmbeddingService()
    print(f"   -> Khởi tạo mô hình xong trong {time.time() - start_init:.2f}s (Vector dimension: {embedder.vector_dim})")

    print(f"\n⚡ Đang thực hiện Vector Embedding cho {len(chunks)} chunks...")
    start_embed = time.time()
    embedded_chunks = embedder.embed_chunks(chunks, batch_size=32)
    elapsed = time.time() - start_embed
    print(f"   -> Đã nhúng hoàn tất {len(embedded_chunks)} chunks trong {elapsed:.2f}s ({elapsed/len(chunks)*1000:.1f}ms/chunk)")

    out_path = Path("debug/06_embedded_chunks.json")
    out_path.write_text(json.dumps(embedded_chunks, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n✅ Đã lưu kết quả Vector Embedding tại: {out_path}")
    sample = embedded_chunks[0]
    print(f"🔍 Kiểm tra mẫu Chunk 1 ({sample['chunk_id']}):")
    print(f"   - Độ dài Vector: {len(sample['vector'])} chiều")
    print(f"   - Vector xem trước (5 phần tử đầu): {sample['vector'][:5]}")

if __name__ == "__main__":
    main()
