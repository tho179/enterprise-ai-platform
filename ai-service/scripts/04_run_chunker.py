import sys
import io
import json
from pathlib import Path
from dataclasses import asdict
from app.adaptive_chunker import AdaptiveChunker

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def main():
    in_path = Path("debug/03_structured_nodes.json")
    if not in_path.exists():
        print(f"❌ Không tìm thấy file {in_path}. Vui lòng chạy 03_run_structure.py trước.")
        return
        
    print(f"✂️ Đang chạy Adaptive Chunking 4 cấp độ từ: {in_path.name}")
    structured_nodes = json.loads(in_path.read_text(encoding="utf-8"))
    
    chunker = AdaptiveChunker()
    chunks = chunker.chunk_nodes(structured_nodes)
    
    # Chuyển TextChunk objects thành dict để lưu JSON
    chunk_dicts = [asdict(c) for c in chunks]
    
    out_path = Path("debug/04_extracted_chunks.json")
    out_path.write_text(json.dumps(chunk_dicts, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"✅ Đã lưu kết quả Chunker ({len(chunks)} chunks) tại: {out_path}")

if __name__ == "__main__":
    main()
