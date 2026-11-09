import unittest

from app.knowledge_graph.extract import build_record_from_ingest_chunks
from app.knowledge_graph.service import graph_hit_from_row, graph_search
from app.rag_service import RAGService


INGEST_CHUNKS = [
    {
        "chunk_id": "doc-d1-v2-c0",
        "chunk_index": 0,
        "content": (
            "Điều 14. Quyền và nghĩa vụ của Đại hội đồng cổ đông. "
            "Hội đồng Quản trị triệu tập họp Đại hội đồng cổ đông."
        ),
        "metadata": {
            "document_id": "d1",
            "document_code": "DL-2026",
            "title": "Điều lệ công ty 2026",
            "document_type": "Quy chế",
            "version_id": "v2",
            "version_number": 2,
            "page_start": 12,
            "page_end": 12,
            "section_path": ["Chương II", "Điều 14"],
        },
    },
    {
        "chunk_id": "doc-d1-v2-c1",
        "chunk_index": 1,
        "content": "Điều 15. Thời hạn hoạt động của Công ty là vô thời hạn.",
        "metadata": {
            "document_id": "d1",
            "document_code": "DL-2026",
            "title": "Điều lệ công ty 2026",
            "document_type": "Quy chế",
            "version_id": "v2",
            "version_number": 2,
            "page_start": 13,
            "page_end": 13,
            "section_path": "Chương III",
        },
    },
]


class TestGraphIngest(unittest.TestCase):
    def test_build_record_keeps_qdrant_chunk_ids(self):
        records = build_record_from_ingest_chunks(INGEST_CHUNKS)

        self.assertEqual(len(records), 1)
        record = records[0]
        self.assertEqual(record["doc"]["doc_id"], "d1")
        self.assertEqual(record["doc"]["title"], "Điều lệ công ty 2026")
        self.assertEqual(record["doc"]["version"], 2)
        self.assertEqual(record["doc"]["version_id"], "v2")
        self.assertEqual(record["doc"]["source_type"], "upload")
        self.assertEqual([chunk["chunk_id"] for chunk in record["chunks"]], [
            "doc-d1-v2-c0",
            "doc-d1-v2-c1",
        ])
        self.assertEqual([chunk["chunk_index"] for chunk in record["chunks"]], [0, 1])
        self.assertEqual(record["chunks"][0]["section_path"], ["Chương II", "Điều 14"])
        self.assertEqual(record["chunks"][1]["section_path"], ["Chương III"])

    def test_build_record_derives_backend_index_and_version(self):
        record = build_record_from_ingest_chunks(
            [
                {
                    "chunk_id": "doc-d2-v3-c7",
                    "content": "Điều 7. Nội dung.",
                    "metadata": {
                        "document_id": "d2",
                        "version_id": "version-uuid",
                        "title": "Quy chế",
                        "page_start": 2,
                        "page_end": 2,
                    },
                }
            ]
        )[0]

        self.assertEqual(record["doc"]["version"], 3)
        self.assertEqual(record["chunks"][0]["chunk_index"], 7)
        self.assertEqual(record["chunks"][0]["version_id"], "version-uuid")

    def test_build_record_keeps_each_chunk_version(self):
        record = build_record_from_ingest_chunks(
            [
                {
                    "chunk_id": "doc-d3-v1-c0",
                    "content": "Điều 1. Bản cũ.",
                    "metadata": {
                        "document_id": "d3",
                        "version_id": "v1",
                        "title": "Quy chế",
                    },
                },
                {
                    "chunk_id": "doc-d3-v2-c0",
                    "content": "Điều 1. Bản mới.",
                    "metadata": {
                        "document_id": "d3",
                        "version_id": "v2",
                        "title": "Quy chế",
                    },
                },
            ]
        )[0]

        self.assertEqual(record["doc"]["version"], 2)
        self.assertEqual(record["doc"]["version_id"], "v2")
        self.assertEqual(
            [chunk["version_id"] for chunk in record["chunks"]],
            ["v1", "v2"],
        )

    def test_build_record_extracts_entities_from_content(self):
        record = build_record_from_ingest_chunks(INGEST_CHUNKS)[0]
        names = {entity["name"] for entity in record["chunks"][0]["entities"]}

        self.assertIn("Điều 14", names)
        self.assertIn("Hội đồng Quản trị", names)
        self.assertIn("Đại hội đồng cổ đông", names)

    def test_graph_hit_keeps_provenance(self):
        hit = graph_hit_from_row(
            {
                "chunk_id": "doc-d1-v2-c0",
                "content": "Điều 14. Quyền của Đại hội đồng cổ đông.",
                "document_id": "d1",
                "title": "Điều lệ công ty 2026",
                "document_type": "Quy chế",
                "page_start": 12,
                "page_end": 12,
                "section_path": ["Chương II", "Điều 14"],
                "matched": 2,
            },
            question="Điều 14 quy định gì?",
        )

        self.assertEqual(hit["chunk_id"], "doc-d1-v2-c0")
        self.assertTrue(hit["from_graph"])
        self.assertTrue(hit["article_match"])
        self.assertGreaterEqual(hit["score"], 0.6)
        self.assertEqual(hit["metadata"]["document_id"], "d1")
        self.assertEqual(hit["metadata"]["section_path"], ["Chương II", "Điều 14"])

    def test_graph_neighbor_ranks_below_direct_hit(self):
        row = {
            "chunk_id": "doc-d1-v2-c0",
            "content": "Điều 14. Quyền của Đại hội đồng cổ đông.",
            "document_id": "d1",
            "title": "Điều lệ công ty 2026",
            "matched": 1,
        }

        direct = graph_hit_from_row({**row, "related": 0})
        neighbor = graph_hit_from_row({**row, "related": 1})

        self.assertGreater(direct["score"], neighbor["score"])
        self.assertEqual(direct["graph_related"], 0)
        self.assertEqual(neighbor["graph_related"], 1)

    def test_graph_search_uses_known_entity_names(self):
        class FakeStore:
            def __init__(self):
                self.names = []

            def entity_names(self, kb_id="KB", limit=5000):
                return []

            def graph_candidates(self, names, kb_ids, limit, source_type=None, document_id=None, allowed_roles=None):
                self.names = list(names)
                return [
                    {
                        "chunk_id": "doc-d1-v2-c0",
                        "content": "Điều 14. Quyền của Đại hội đồng cổ đông.",
                        "document_id": "d1",
                        "title": "Điều lệ công ty 2026",
                        "document_type": "Quy chế",
                        "page_start": 12,
                        "page_end": 12,
                        "section_path": ["Chương II", "Điều 14"],
                        "matched": 1,
                    }
                ]

        store = FakeStore()
        hits = graph_search(
            "Điều 14 quy định gì?",
            store=store,
            enabled=True,
        )

        self.assertEqual(len(hits), 1)
        self.assertIn("Điều 14", store.names)

    def test_graph_search_is_off_when_disabled(self):
        self.assertEqual(graph_search("Điều 14 quy định gì?", enabled=False), [])

    def test_fuse_hits_keeps_vector_score_and_fills_graph_metadata(self):
        vector_hits = [
            {"chunk_id": "a", "content": "A", "score": 0.8, "metadata": {}},
            {"chunk_id": "b", "content": "B", "score": 0.7, "metadata": {}},
        ]
        graph_hits = [
            {
                "chunk_id": "b",
                "content": "B",
                "score": 0.6,
                "metadata": {"title": "T"},
                "from_graph": True,
            },
            {
                "chunk_id": "c",
                "content": "C",
                "score": 0.55,
                "metadata": {},
                "from_graph": True,
            },
        ]

        fused = RAGService._fuse_hits(vector_hits, graph_hits)

        self.assertEqual({hit["chunk_id"] for hit in fused}, {"a", "b", "c"})
        self.assertEqual(fused[0]["chunk_id"], "b")
        shared = next(hit for hit in fused if hit["chunk_id"] == "b")
        self.assertEqual(shared["score"], 0.7)
        self.assertEqual(shared["metadata"]["title"], "T")
        self.assertIn("rrf_score", shared)


if __name__ == "__main__":
    unittest.main()
