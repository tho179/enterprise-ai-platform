import unittest

import pymupdf
from fastapi.testclient import TestClient

from app.api.v1.extract import build_extract_chunks
from app.main import app


class TestExtractChunks(unittest.TestCase):
    def test_structure_chunks_from_pages(self):
        chunks = build_extract_chunks(
            [
                {
                    "page": 1,
                    "text": (
                        "CHƯƠNG I. QUY ĐỊNH CHUNG\n"
                        "Điều 1. Phạm vi điều chỉnh\n"
                        "Tài liệu này quy định cơ cấu tổ chức, quyền và nghĩa vụ "
                        "của các thành viên trong công ty.\n"
                        "Điều 2. Đối tượng áp dụng\n"
                        "Quy định này áp dụng cho toàn bộ thành viên và người lao động."
                    ),
                }
            ]
        )

        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(chunks[0].index, 0)
        self.assertEqual(chunks[0].pageStart, 1)
        self.assertIn("Điều 1", chunks[0].content)
        self.assertTrue(chunks[0].sectionPath)
        self.assertIn("CHƯƠNG I", chunks[0].sectionPath[0])

    def test_extract_endpoint_returns_chunks(self):
        document = pymupdf.open()
        page = document.new_page()
        page.insert_text(
            (72, 72),
            "CHUONG I. QUY DINH CHUNG\n"
            "Dieu 1. Pham vi dieu chinh\n"
            "Tai lieu nay quy dinh co cau to chuc, quyen va nghia vu cua "
            "cac thanh vien trong cong ty.",
        )
        pdf_bytes = document.tobytes()
        document.close()

        response = TestClient(app).post(
            "/api/v1/extract",
            files={"file": ("chunks.pdf", pdf_bytes, "application/pdf")},
        )

        self.assertEqual(response.status_code, 200, response.text)
        chunks = response.json()["chunks"]
        self.assertGreaterEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["index"], 0)
        self.assertEqual(chunks[0]["pageStart"], 1)


if __name__ == "__main__":
    unittest.main()
