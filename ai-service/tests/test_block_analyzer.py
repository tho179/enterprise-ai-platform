import unittest
from app.block_analyzer import BlockAnalyzer

class TestBlockAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = BlockAnalyzer()

    def test_classify_and_split(self):
        sample_pages = [
            {
                "page": 1,
                "text": "CÔNG TY ABC\nQuyết định thành lập\n\nĐiều 1: Tên công ty\nCông ty cổ phần ABC.\n\nĐiều 2. Trụ sở\nTại Hà Nội."
            }
        ]
        
        blocks = self.analyzer.analyze(sample_pages)
        
        # Sẽ có 3 block: Mở đầu, Điều 1, Điều 2
        self.assertEqual(len(blocks), 3)
        
        self.assertEqual(blocks[0]["title"], "Phần mở đầu")
        self.assertEqual(blocks[0]["label"], "Unstructured")
        
        self.assertTrue("Điều 1" in blocks[1]["title"])
        self.assertEqual(blocks[1]["label"], "Structured")
        
        self.assertTrue("Điều 2" in blocks[2]["title"])

if __name__ == "__main__":
    unittest.main()
