import unittest
from app.block_analyzer import BlockAnalyzer
from app.structure_analyzer import HierarchyResolver
from app.adaptive_chunker import AdaptiveChunker


class TestHierarchyStability(unittest.TestCase):
    def setUp(self):
        self.analyzer = BlockAnalyzer()
        self.resolver = HierarchyResolver()

    def test_toc_exit_on_any_article(self):
        """TOC phải thoát ở Điều 2/3, không chỉ Điều 1 (bug cũ nuốt heading thành TOC)."""
        pages = [
            {"page": 1, "text": "Mục lục\nChương I .................... 1\nĐiều 1 .................... 2"},
            {"page": 2, "text": "CHƯƠNG I\nQUY ĐỊNH CHUNG"},
            {"page": 2, "text": "Điều 1. Phạm vi áp dụng."},
            {"page": 3, "text": "Điều 2. Đối tượng áp dụng."},
            {"page": 4, "text": "Điều 3. Giải thích từ ngữ."},
        ]
        nodes = self.resolver.resolve(self.analyzer.analyze(pages))
        dieu2 = [n for n in nodes if "Điều 2" in n["text"]]
        dieu3 = [n for n in nodes if "Điều 3" in n["text"]]
        self.assertTrue(dieu2 and dieu2[0]["block_type"] == "HEADING")
        self.assertTrue(dieu3 and dieu3[0]["block_type"] == "HEADING")

    def test_depth_levels_distinct(self):
        """PART/CHAPTER/ARTICLE/SECTION/NUMBERED phải có depth phân biệt."""
        pages = [{"page": 1, "text": "PHẦN I. NHỮNG QUY ĐỊNH CHUNG."},
                 {"page": 1, "text": "CHƯƠNG I. QUY ĐỊNH CHUNG."},
                 {"page": 1, "text": "Điều 1. Phạm vi điều chỉnh."},
                 {"page": 1, "text": "Mục 1. Nguyên tắc chung."}]
        nodes = self.resolver.resolve(self.analyzer.analyze(pages))
        depths = {n["heading_type"]: n["depth"] for n in nodes if n["block_type"] == "HEADING"}
        self.assertLess(depths["PART"], depths["CHAPTER"])
        self.assertLess(depths["CHAPTER"], depths["ARTICLE"])
        self.assertLess(depths["ARTICLE"], depths["SECTION"])

    def test_heading_not_merged_with_content(self):
        """Heading ngắn + câu nội dung phải tách node, không gộp."""
        pages = [{"page": 5, "text": "Điều 5. Thử việc"},
                 {"page": 5, "text": "Nội dung thử việc chi tiết."}]
        nodes = self.resolver.resolve(self.analyzer.analyze(pages))
        headings = [n for n in nodes if n["block_type"] == "HEADING"]
        paras = [n for n in nodes if n["block_type"] == "PARAGRAPH"]
        self.assertEqual(len(headings), 1)
        self.assertEqual(len(paras), 1)
        self.assertEqual(paras[0]["section_path"][-1], headings[0]["text"])


class TestChunkingBoundary(unittest.TestCase):
    def setUp(self):
        self.analyzer = BlockAnalyzer()
        self.resolver = HierarchyResolver()

    def _resolve(self, pages):
        return self.resolver.resolve(self.analyzer.analyze(pages))

    def test_no_orphan_empty_path_chunk(self):
        pages = [
            {"page": 4, "text": "Lời nói đầu của công ty, đoạn mở đầu chưa vào chương nào."},
            {"page": 4, "text": "CHƯƠNG II\nCHẾ ĐỘ LAO ĐỘNG."},
            {"page": 5, "text": "Điều 5. Thử việc."},
            {"page": 5, "text": "Nội dung thử việc chi tiết."},
        ]
        chunks = AdaptiveChunker().chunk_nodes(self._resolve(pages))
        self.assertGreater(len(chunks), 0)
        self.assertEqual(sum(1 for c in chunks if not c.metadata.get("section_path")), 0)

    def test_page_range_and_section_type(self):
        pages = [
            {"page": 4, "text": "CHƯƠNG II\nCHẾ ĐỘ LAO ĐỘNG."},
            {"page": 5, "text": "Điều 5. Thử việc."},
            {"page": 6, "text": "Nội dung thử việc chi tiết, kéo dài thêm để đủ độ dài chunk."},
        ]
        chunks = AdaptiveChunker().chunk_nodes(self._resolve(pages))
        for c in chunks:
            self.assertIn("page_start", c.metadata)
            self.assertIn("page_end", c.metadata)
            self.assertLessEqual(c.metadata["page_start"], c.metadata["page_end"])
            self.assertIsNotNone(c.metadata.get("section_type"))

    def test_sentence_split_keeps_outline(self):
        ch = AdaptiveChunker()
        sents = ch._split_sentences(
            "1. Mục đích của quy chế này rất rõ ràng. Nội dung tiếp theo. "
            "1.1. Phạm vi áp dụng cụ thể. Giải thích thêm."
        )
        self.assertTrue(sents[0].startswith("1. Mục đích"))
        self.assertTrue(any(s.startswith("1.1. Phạm vi") for s in sents))


if __name__ == "__main__":
    unittest.main()
