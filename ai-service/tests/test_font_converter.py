import unittest
from app.font_converter import normalize_vietnamese_text


class TestFontConverter(unittest.TestCase):
    def test_tcvn3_conversion(self):
        # TCVN3 encoded sample with multiple markers
        tcvn3_text = "C\xb5ng h\xb8a x\xb7 h\xb9i ch\xbc ngh\xdfa Vi\xbe\xca t Nam"
        result = normalize_vietnamese_text(tcvn3_text)
        self.assertNotEqual(result, tcvn3_text)

    def test_unicode_text_remains_unchanged(self):
        unicode_text = "Cộng hòa xã hội chủ nghĩa Việt Nam"
        result = normalize_vietnamese_text(unicode_text)
        self.assertEqual(result, unicode_text)


if __name__ == "__main__":
    unittest.main()
