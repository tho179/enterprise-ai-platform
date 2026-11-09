import unittest

from app.knowledge_graph.extract import (
    build_link_record,
    build_record_from_pages,
    extract_entities,
    html_to_text,
)
from app.knowledge_graph.ids import document_id
from app.knowledge_graph.pipeline import plan_update, rrf_fuse


PAGE = {
    "page": 12,
    "text": (
        "Điều 14. Quyền và nghĩa vụ của Đại hội đồng cổ đông\n"
        "1. Đại hội đồng cổ đông có các quyền và nghĩa vụ sau: thông qua định hướng "
        "phát triển của Công ty; thông qua báo cáo tài chính năm đã kiểm toán; quyết "
        "định mức cổ tức thanh toán hằng năm cho mỗi loại cổ phần.\n"
        "2. Chủ tịch Hội đồng Quản trị triệu tập họp Đại hội đồng cổ đông trong thời "
        "hạn luật định. Tổng Giám đốc chuẩn bị tài liệu họp và công bố thông tin."
    ),
}


class TestKnowledgeGraph(unittest.TestCase):
    def test_document_id_is_content_addressed(self):
        first = document_id("hash-a", "Điều lệ Công ty")
        second = document_id("hash-a", "Điều lệ Công ty")
        changed = document_id("hash-b", "Điều lệ Công ty")
        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)

    def test_extract_entities_roles_and_articles(self):
        entities = extract_entities(PAGE["text"])
        names = {entity["name"] for entity in entities}
        self.assertIn("Điều 14", names)
        self.assertIn("Cổ tức", names)
        self.assertIn("Chủ tịch Hội đồng Quản trị", names)
        self.assertIn("Tổng Giám đốc", names)
        self.assertIn("Đại hội đồng cổ đông", names)

    def test_build_record_has_chunks_and_section_path(self):
        record = build_record_from_pages(
            title="Điều lệ Công ty",
            source_uri="data/Dieu_le.pdf",
            source_type="pdf",
            pages=[PAGE],
        )
        self.assertTrue(record["doc"]["doc_id"].startswith("doc-"))
        self.assertGreaterEqual(len(record["chunks"]), 1)
        self.assertEqual(record["chunks"][0]["page_start"], 12)
        self.assertTrue(record["chunks"][0]["section_path"])
        self.assertTrue(record["chunks"][0]["entities"])

    def test_html_to_text_and_link_record(self):
        html = """
        <html><head><title>Quản trị công ty</title>
        <style>body{display:none}</style></head>
        <body><nav>Menu</nav><h1>Quản trị công ty</h1>
        <p>Hội đồng Quản trị có vai trò định hướng chiến lược.</p>
        <script>alert(1)</script></body></html>
        """
        title, text = html_to_text(html)
        self.assertEqual(title, "Quản trị công ty")
        self.assertIn("Hội đồng Quản trị", text)
        self.assertNotIn("alert", text)
        record = build_link_record("https://example.test/quan-tri", html=html)
        self.assertEqual(record["doc"]["source_type"], "web")
        self.assertEqual(record["doc"]["source_uri"], "https://example.test/quan-tri")

    def test_plan_update(self):
        self.assertEqual(plan_update(None, "h1"), "insert")
        self.assertEqual(plan_update({"content_hash": "h1"}, "h1"), "skip")
        self.assertEqual(plan_update({"content_hash": "h1"}, "h2"), "new_version")

    def test_rrf_fuse_keeps_both_sources(self):
        vector = [{"chunk_id": "a", "content": "A"}, {"chunk_id": "b", "content": "B"}]
        graph = [{"chunk_id": "b", "content": "B"}, {"chunk_id": "c", "content": "C"}]
        fused = rrf_fuse(vector, graph)
        self.assertEqual({hit["chunk_id"] for hit in fused}, {"a", "b", "c"})
        self.assertEqual(fused[0]["chunk_id"], "b")


if __name__ == "__main__":
    unittest.main()
