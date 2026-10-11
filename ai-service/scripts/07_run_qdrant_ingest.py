import sys
import io
import json
import time
from pathlib import Path

from app.qdrant_service import QdrantService

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def main():
    in_path = Path("debug/06_embedded_chunks.json")
    if not in_path.exists():
        print(f"❌ Không tìm thấy file {in_path}. Vui lòng chạy 06_run_embedding.py trước.")
        return

    print(f"📂 Đang đọc dữ liệu vector chunks từ: {in_path.name}")
    chunks = json.loads(in_path.read_text(encoding="utf-8"))
    print(f"   -> Tìm thấy {len(chunks)} chunks kèm vector.")

    print(f"\n📡 Đang kết nối tới Qdrant Vector Database...")
    qdrant = QdrantService()

    print(f"📥 Đang nạp dữ liệu (Upsert) vào Qdrant...")
    start_time = time.time()
    count = qdrant.upsert_chunks(chunks, batch_size=64)
    elapsed = time.time() - start_time
    print(f"   -> Nạp thành công {count} vectors trong {elapsed:.2f}s ({elapsed/count*1000:.1f}ms/chunk)")

    total_in_db = qdrant.count()
    print(f"\n✅ Tổng số vectors trong Qdrant Collection '{qdrant.collection_name}': {total_in_db} points")

if __name__ == "__main__":
    main()
