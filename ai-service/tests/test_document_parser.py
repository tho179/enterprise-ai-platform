import unittest
from pathlib import Path
from app.document_parser import extract_text, extract_text_from_pdf, extract_text_from_txt


class TestDocumentParser(unittest.TestCase):
    def test_extract_scanned_pdf(self):
        pdf_path = Path("data/documents/dieu_le_sua_doi/Phu_luc_sua_doi_dieu_le_lan_1.pdf")
        if not pdf_path.exists():
            self.skipTest(f"File không tồn tại: {pdf_path}")

        pages = extract_text_from_pdf(str(pdf_path))
        self.assertGreater(len(pages), 0)
        self.assertIn("page", pages[0])
        self.assertIn("text", pages[0])
        self.assertIn("source", pages[0])
        self.assertIn("words", pages[0])
        self.assertEqual(pages[0]["source"], "ocr", "Nguồn phải là ocr do file này là PDF Scan")
        self.assertGreater(len(pages[0]["text"]), 20)
        self.assertGreater(len(pages[0]["words"]), 0)

    def test_extract_native_pdf(self):
        pdf_path = Path("data/documents/dieu_le_sua_doi/Phu_luc_sua_doi_dieu_le_lan_khac.pdf")
        if not pdf_path.exists():
            self.skipTest(f"File không tồn tại: {pdf_path}")

        pages = extract_text_from_pdf(str(pdf_path))
        self.assertGreater(len(pages), 0)
        self.assertEqual(pages[0]["source"], "native", "Nguồn phải là native do file này có text layer")
        self.assertGreater(len(pages[0]["words"]), 0)
        # Kiểm tra cấu trúc bounding box
        word = pages[0]["words"][0]
        self.assertIn("x", word)
        self.assertIn("y", word)
        self.assertIn("width", word)
        self.assertIn("height", word)
        self.assertIn("confidence", word)

    def test_extract_txt_file(self):
        txt_path = Path("data/test_sample.txt")
        txt_path.write_text("Cộng hòa xã hội chủ nghĩa Việt Nam\nĐộc lập - Tự do - Hạnh phúc", encoding="utf-8")
        try:
            pages = extract_text_from_txt(str(txt_path))
            self.assertEqual(len(pages), 1)
            self.assertEqual(pages[0]["page"], 1)
            self.assertIn("Cộng hòa", pages[0]["text"])
        finally:
            if txt_path.exists():
                txt_path.unlink()


if __name__ == "__main__":
    unittest.main()
