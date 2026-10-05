import unittest
import json
from pathlib import Path
from app.block_analyzer import BlockAnalyzer, BlockType, HeadingType
from app.structure_analyzer import HierarchyResolver

class TestBlockAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = BlockAnalyzer()
        self.resolver = HierarchyResolver()
        self.output_dir = Path("data/test_outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.test_results = {}

    def tearDown(self):
        output_file = self.output_dir / "test_output_block_analyzer.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)

    def test_legal_document_structure(self):
        pages = [{
            "page": 1,
            "text": "CHƯƠNG I\nQUY ĐỊNH CHUNG\nĐiều 1. Phạm vi áp dụng\n1. Quy chế này quy định...\na) Đối với nhân viên...\n- Nghỉ thai sản\n- Nghỉ ốm"
        }]
        raw_nodes = self.analyzer.analyze(pages)
        nodes = self.resolver.resolve(raw_nodes)
        self.test_results["legal_document_structure"] = nodes
        
        self.assertEqual(nodes[0]["block_type"], BlockType.HEADING)
        # V3 gộp "CHƯƠNG I" và "QUY ĐỊNH CHUNG" thành 1 vì không có dấu câu
        self.assertEqual(nodes[0]["section_path"], ["CHƯƠNG I QUY ĐỊNH CHUNG"])
        self.assertEqual(nodes[1]["section_path"], ["CHƯƠNG I QUY ĐỊNH CHUNG", "Điều 1. Phạm vi áp dụng"])

    def test_process_document_structure(self):
        pages = [{
            "page": 1,
            "text": "I. Tổng quan\n1. Mục đích\n1.1. Phạm vi.\nĐây là phần giải thích phạm vi."
        }]
        raw_nodes = self.analyzer.analyze(pages)
        nodes = self.resolver.resolve(raw_nodes)
        self.test_results["process_document_structure"] = nodes
        
        self.assertEqual(nodes[0]["section_path"], ["I. Tổng quan"])
        self.assertEqual(nodes[1]["section_path"], ["I. Tổng quan", "1. Mục đích"])
        # Có dấu chấm sau Phạm vi nên không bị gộp
        self.assertEqual(nodes[2]["section_path"], ["I. Tổng quan", "1. Mục đích", "1.1. Phạm vi."])

    def test_false_heading_trap(self):
        pages = [{
            "page": 1,
            "text": "1. Người lao động phải tuân thủ nghiêm ngặt các quy định về an toàn lao động trong suốt quá trình làm việc tại nhà máy để đảm bảo không xảy ra sự cố đáng tiếc nào."
        }]
        raw_nodes = self.analyzer.analyze(pages)
        nodes = self.resolver.resolve(raw_nodes)
        self.test_results["false_heading_trap"] = nodes
        self.assertIn(nodes[0]["block_type"], [BlockType.LIST_ITEM, BlockType.PARAGRAPH])

    def test_ocr_resilience(self):
        pages = [{
            "page": 1,
            "text": "diều 1. Lỗi chữ d\nđieu 2. Lỗi mất dấu nón"
        }]
        raw_nodes = self.analyzer.analyze(pages)
        nodes = self.resolver.resolve(raw_nodes)
        self.test_results["ocr_resilience"] = nodes
        # Với V3, đieu và diều chưa nằm trong regex is_structure_start nên có thể bị merge.
        # Ta check có node nào nhận diện là ARTICLE không
        has_article = any(n["heading_type"] == HeadingType.ARTICLE for n in nodes)
        self.assertTrue(has_article)

    def test_toc_filter(self):
        pages = [{
            "page": 1,
            "text": "Chương I ....................... 1\nĐiều 1 ......................... 2\nEEEEEEEEEE 3"
        }]
        raw_nodes = self.analyzer.analyze(pages)
        nodes = self.resolver.resolve(raw_nodes)
        self.test_results["toc_filter"] = nodes
        # V4 đánh dấu rác bằng is_garbage thay vì drop thẳng.
        # "EEEEEEEEEE 3" và "Chương I ........... 1" sẽ bị bắt bởi regex \1{5,}
        has_garbage = any(n["is_garbage"] for n in nodes)
        self.assertTrue(has_garbage)

if __name__ == "__main__":
    unittest.main()
