import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class BlockAnalyzer:
    """
    Block Analyzer (Bộ phân tích khối văn bản)
    Nhiệm vụ: Duyệt qua văn bản gốc từ Parser và chia nhỏ (chunking) 
    dựa trên các dấu hiệu ngữ nghĩa thay vì cắt cứng theo số lượng từ.
    """
    def __init__(self):
        # Biểu thức chính quy (Regex) bắt các dấu hiệu nhận biết cấu trúc
        self.markers = {
            "chapter": re.compile(r"(?i)^chương\s+[ivxlcdm]+[\.\:]?\s*(.*)", re.MULTILINE),
            "article": re.compile(r"(?i)^điều\s+\d+[\.\:]?\s*(.*)", re.MULTILINE),
            "roman_section": re.compile(r"^[IVXLCDM]+[\.\:]\s+(.*)", re.MULTILINE),
            "decimal_section": re.compile(r"^\d+[\.\:]\s+(.*)", re.MULTILINE),
        }
        
    def _is_toc_line(self, line: str) -> bool:
        """
        Nhận diện dòng Mục lục: thường kết thúc bằng dải dấu chấm/gạch và số trang.
        Tuy nhiên do OCR có thể nhận diện sai thành các dải chữ (EEEEE, nnnnn), ta cần bắt cả nhiễu.
        """
        # 1. Bắt dải từ 5 dấu chấm/gạch trở lên (đặc trưng nhất của mục lục)
        if bool(re.search(r'(?:\.{5,}|_{5,})', line)):
            return True
            
        # 2. Bắt các dải chữ/số lặp lại vô nghĩa do OCR đọc sai dấu chấm (ví dụ: EEEEE, nnnnn)
        if bool(re.search(r'([a-zA-Z0-9])\1{5,}', line)):
            return True
            
        return False
        
    def _classify_block(self, text: str) -> str:
        """
        Gán nhãn loại dữ liệu cho block.
        """
        # Nếu đoạn chứa nhiều con số, tab hoặc ký hiệu đặc biệt dạng bảng -> Semi-structured
        if text.count('\t') > 3 or len(re.findall(r'[\d\.\,]{3,}', text)) > 5:
            return "Semi-structured"
        
        # Nếu có dấu hiệu của Chương, Điều, Mục La Mã -> Structured
        if (self.markers["chapter"].search(text) or 
            self.markers["article"].search(text) or 
            self.markers["roman_section"].search(text)):
            return "Structured"
            
        return "Unstructured"

    def analyze(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Phân tích mảng pages đầu vào và xuất ra mảng blocks.
        """
        blocks = []
        
        # Tách toàn bộ văn bản thành từng dòng để duyệt phân cấp (Hierarchical Parsing)
        full_text = "\n".join([p["text"] for p in pages if p.get("text")])
        lines = full_text.split('\n')
        
        current_chapter = ""
        current_roman = ""
        current_title = "Phần mở đầu"
        current_content = []
        
        # Đánh giá sơ bộ xem tài liệu này có dùng "Điều" hay không
        has_articles = bool(re.search(r"(?i)^điều\s+\d+", full_text, re.MULTILINE))
        
        def save_block():
            text = "\n".join(current_content).strip()
            if text:
                blocks.append({
                    "block_id": len(blocks) + 1,
                    "parent_chapter": current_chapter,
                    "parent_section": current_roman,
                    "title": current_title,
                    "label": self._classify_block(text),
                    "content": text
                })
            current_content.clear()

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue
                
            # Bỏ qua rác từ Mục lục (Table of Contents)
            if self._is_toc_line(line_str):
                continue
                
            # 1. Bắt cấu trúc Chương
            if self.markers["chapter"].match(line_str):
                save_block()
                current_chapter = line_str
                current_title = line_str
                current_content.append(line_str)
                continue
                
            # 2. Bắt cấu trúc Mục La Mã (I., II.)
            if self.markers["roman_section"].match(line_str):
                save_block()
                current_roman = line_str
                current_title = line_str
                current_content.append(line_str)
                continue
                
            # 3. Bắt cấu trúc Điều (Điều 1, Điều 2)
            if self.markers["article"].match(line_str):
                save_block()
                current_title = line_str
                current_content.append(line_str)
                continue
                
            # 4. Nếu tài liệu KHÔNG HỀ CÓ "Điều", ta mới cho phép cắt theo mục đếm số (1., 2.)
            if not has_articles and self.markers["decimal_section"].match(line_str):
                save_block()
                current_title = line_str
                current_content.append(line_str)
                continue
                
            # Nếu không phải tiêu đề, cứ cộng dồn vào nội dung của block hiện tại
            current_content.append(line)

        # Lưu block cuối cùng còn sót lại
        save_block()
        
        return blocks
