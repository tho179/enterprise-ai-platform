import unittest
import json
import os
from pathlib import Path
from app.document_parser import extract_text_from_pdf, extract_text_from_txt

class TestDocumentParser(unittest.TestCase):
    def setUp(self):
        self.output_dir = Path("data/test_outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.test_results = {}

    def tearDown(self):
        output_file = self.output_dir / "test_output_document_parser.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2)

    def test_extract_scanned_pdf(self):
        pdf_path = Path("data/documents/dieu_le_sua_doi/Phu_luc_sua_doi_dieu_le_lan_1.pdf")
        if not pdf_path.exists():
            self.skipTest(f"File không tồn tại: {pdf_path}")

        pages = extract_text_from_pdf(str(pdf_path))
        self.test_results["scanned_pdf"] = pages
        
        self.assertGreater(len(pages), 0)
        self.assertEqual(pages[0]["source"], "ocr")

    def test_extract_native_pdf(self):
        pdf_path = Path("data/documents/dieu_le_sua_doi/Phu_luc_sua_doi_dieu_le_lan_khac.pdf")
        if not pdf_path.exists():
            self.skipTest(f"File không tồn tại: {pdf_path}")

        pages = extract_text_from_pdf(str(pdf_path))
        self.test_results["native_pdf"] = pages
        
        self.assertGreater(len(pages), 0)
        self.assertEqual(pages[0]["source"], "native")

if __name__ == "__main__":
    unittest.main()
