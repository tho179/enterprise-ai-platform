import sys
import io
import json
from pathlib import Path
from app.block_analyzer import BlockAnalyzer

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def main():
    in_path = Path("debug/01_extracted_pages.json")
    if not in_path.exists():
        print(f"❌ Không tìm thấy file {in_path}. Vui lòng chạy 01_run_extractor.py trước.")
        return
        
    print(f"🔍 Đang phân tích các block văn bản từ: {in_path.name}")
    pages = json.loads(in_path.read_text(encoding="utf-8"))
    
    analyzer = BlockAnalyzer()
    raw_nodes = analyzer.analyze(pages)
    
    # BlockAnalyzer trả về list[StructureNode]. Ta chuyển về dict để lưu JSON.
    nodes_dict = [n.to_dict() for n in raw_nodes]
    
    out_path = Path("debug/02_analyzed_nodes.json")
    out_path.write_text(json.dumps(nodes_dict, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"✅ Đã lưu kết quả Analyzer ({len(raw_nodes)} blocks) tại: {out_path}")

if __name__ == "__main__":
    main()
