import sys
import io
import json
from pathlib import Path
from app.structure_analyzer import HierarchyResolver
from app.block_analyzer import StructureNode, BlockType, HeadingType

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def main():
    in_path = Path("debug/02_analyzed_nodes.json")
    if not in_path.exists():
        print(f"❌ Không tìm thấy file {in_path}. Vui lòng chạy 02_run_analyzer.py trước.")
        return
        
    print(f"🌳 Đang xây dựng cây phả hệ (Structure Tree) từ: {in_path.name}")
    nodes_data = json.loads(in_path.read_text(encoding="utf-8"))
    
    # Tái tạo lại đối tượng StructureNode từ JSON dict
    raw_nodes = []
    for d in nodes_data:
        node = StructureNode(
            id=d["id"],
            text=d["text"],
            page=d["page"]
        )
        # Xử lý gán Enum từ String an toàn
        node.block_type = getattr(BlockType, d["block_type"]) if d.get("block_type") else None
        node.heading_type = getattr(HeadingType, d["heading_type"]) if d.get("heading_type") else None
        node.list_type = d.get("list_type")
        node.depth = d.get("depth", -1)
        node.ocr_confidence = d.get("ocr_confidence", 1.0)
        node.classifier_confidence = d.get("classifier_confidence", 1.0)
        node.is_garbage = d.get("is_garbage", False)
        
        raw_nodes.append(node)
    
    resolver = HierarchyResolver()
    resolved_nodes = resolver.resolve(raw_nodes)
    
    out_path = Path("debug/03_structured_nodes.json")
    out_path.write_text(json.dumps(resolved_nodes, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"✅ Đã lưu kết quả Cây cấu trúc ({len(resolved_nodes)} nodes) tại: {out_path}")

if __name__ == "__main__":
    main()
