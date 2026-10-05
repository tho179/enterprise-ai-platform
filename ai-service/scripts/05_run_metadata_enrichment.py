import sys
import io
import json
from pathlib import Path
from app.metadata_enricher import MetadataEnricher

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def main():
    in_path = Path("debug/04_extracted_chunks.json")
    if not in_path.exists():
        print(f"❌ Không tìm thấy file {in_path}. Vui lòng chạy 04_run_chunker.py trước.")
        return
        
    print(f"🏷️ Đang chạy Metadata Enrichment cho Dữ liệu từ: {in_path.name}")
    chunks_data = json.loads(in_path.read_text(encoding="utf-8"))
    
    # Khởi tạo Enricher với dữ liệu giả lập được truyền từ Backend (Spring Boot)
    enricher = MetadataEnricher(
        document_id="DOC-001",
        version_id="VER-001",
        document_type="regulation",
        language="vi"
    )
    
    enriched_chunks = enricher.enrich(chunks_data)
    
    out_path = Path("debug/05_enriched_chunks.json")
    out_path.write_text(json.dumps(enriched_chunks, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"✅ Đã lưu kết quả Metadata Enrichment ({len(enriched_chunks)} chunks) tại: {out_path}")
    print(f"Bây giờ Dữ liệu đã SẴN SÀNG để nhúng (Embedding) và đưa vào Qdrant/Neo4j!")

if __name__ == "__main__":
    main()
