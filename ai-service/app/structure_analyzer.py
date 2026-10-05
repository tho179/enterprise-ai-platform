from typing import List, Tuple, Dict, Any
import re
from app.block_analyzer import StructureNode, BlockType, HeadingType

class HierarchyResolver:
    """
    Structure Analyzer V3 - Hierarchy Resolver
    Phân tích quan hệ cha con và gán section_path/depth
    """
    def resolve(self, nodes: List[StructureNode]) -> List[Dict[str, Any]]:
        current_path: List[Tuple[int, str]] = []
        in_toc = False
        resolved_nodes = []
        
        for node in nodes:
            # 1. TOC Bypasser bằng Heuristic (Dựa vào số lượng dấu chấm)
            # OCR sinh ra rác quá khủng khiếp (ví dụ: ...En E E EE EE.7 4)
            # Thực tế: Không có Heading hay đoạn văn chuẩn mực nào chứa 6 dấu chấm/gạch dưới liên tiếp.
            is_toc_item = bool(re.search(r'(?:\.{6,}|…{3,}|_{6,})', node.text))
            
            if node.block_type == BlockType.TOC or is_toc_item:
                in_toc = True
                node.block_type = BlockType.TOC
                resolved_nodes.append(node.to_dict())
                continue
                
            if in_toc:
                # Thoát TOC nếu gặp Heading chính thức (Chương 1, Điều 1) VÀ KHÔNG PHẢI là dòng TOC
                if not is_toc_item and re.match(r"(?i)^(chương\s+[i1vxlcdm]|phần\s+[i1vxlcdm]|điều\s+1[\.\:\-])", node.text):
                    in_toc = False
                else:
                    node.block_type = BlockType.TOC
                    resolved_nodes.append(node.to_dict())
                    continue
                    
            # 2. Hierarchy Logic (Dynamic Structure Tree)
            if node.block_type == BlockType.HEADING:
                # QUAN TRỌNG: Xóa toàn bộ các node cũ trong path có depth >= node hiện tại.
                current_path = [p for p in current_path if p[0] < node.depth]
                current_path.append((node.depth, node.text))
                node.section_path = [p[1] for p in current_path]
            elif node.block_type == BlockType.LIST_ITEM:
                # LIST_ITEM kế thừa section_path, và được cộng thêm 1 cấp depth hoặc giữ cứng depth
                node.section_path = [p[1] for p in current_path]
                node.depth = current_path[-1][0] + 1 if current_path else 1
            else:
                node.section_path = [p[1] for p in current_path]
                
            resolved_nodes.append(node.to_dict())
            
        return resolved_nodes
