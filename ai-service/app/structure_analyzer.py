from typing import List, Tuple, Dict, Any
import re
from app.block_analyzer import StructureNode, BlockType, HeadingType

class HierarchyResolver:
    """
    Structure Analyzer V4 - Hierarchy Resolver
    Phân tích quan hệ cha con, gán section_path/depth và loại bỏ Mục lục (TOC)
    """
    def resolve(self, nodes: List[StructureNode], drop_toc: bool = True) -> List[Dict[str, Any]]:
        current_path: List[Tuple[int, str]] = []
        current_types: List[str] = []   # heading_type of each level in current_path
        resolved_nodes = []
        
        for node in nodes:
            # 1. Loại bỏ TOC khỏi Cây cấu trúc văn bản (Drop sớm để bảo vệ RAG/Graph)
            if node.block_type == BlockType.TOC:
                if drop_toc:
                    continue
                resolved_nodes.append(node.to_dict())
                continue
                
            # 2. Hierarchy Logic (Dynamic Structure Tree)
            if node.block_type == BlockType.HEADING:
                # QUAN TRỌNG: Xóa toàn bộ các node cũ trong path có depth >= node hiện tại.
                keep = [i for i, p in enumerate(current_path) if p[0] < node.depth]
                current_path = [current_path[i] for i in keep]
                current_types = [current_types[i] for i in keep]
                current_path.append((node.depth, node.text))
                current_types.append(node.heading_type.value if node.heading_type else "HEADING")
                node.section_path = [p[1] for p in current_path]
            elif node.block_type == BlockType.LIST_ITEM:
                # LIST_ITEM kế thừa section_path, và được cộng thêm 1 cấp depth hoặc giữ cứng depth
                node.section_path = [p[1] for p in current_path]
                node.depth = current_path[-1][0] + 1 if current_path else 1
            else:
                node.section_path = [p[1] for p in current_path]

            item = node.to_dict()
            # Kind of the innermost section; text before the first heading is the preamble.
            item["section_type"] = current_types[-1] if current_types else "PREAMBLE"
            resolved_nodes.append(item)
            
        return resolved_nodes
