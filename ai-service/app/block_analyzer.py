import re
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class BlockType(str, Enum):
    HEADING = "HEADING"
    PARAGRAPH = "PARAGRAPH"
    LIST_ITEM = "LIST_ITEM"
    TABLE = "TABLE"
    TOC = "TOC"

class HeadingType(str, Enum):
    PART = "PART"
    CHAPTER = "CHAPTER"
    ARTICLE = "ARTICLE"
    SECTION = "SECTION"
    NUMBERED = "NUMBERED"

@dataclass
class StructureNode:
    id: int
    text: str
    block_type: BlockType = BlockType.PARAGRAPH
    heading_type: Optional[HeadingType] = None
    list_type: Optional[str] = None # 'ALPHA', 'BULLET'
    
    page: int = 1
    font_size: float = 12.0
    is_bold: bool = False
    
    depth: int = -1
    ocr_confidence: float = 0.95 # Giá trị giả lập chờ OCR cung cấp
    classifier_confidence: float = 0.0
    is_garbage: bool = False
    section_path: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "id": self.id,
            "text": self.text,
            "block_type": self.block_type.value,
            "heading_type": self.heading_type.value if self.heading_type else None,
            "list_type": self.list_type,
            "depth": self.depth,
            "ocr_confidence": self.ocr_confidence,
            "classifier_confidence": self.classifier_confidence,
            "is_garbage": self.is_garbage,
            "section_path": self.section_path,
            "page": self.page
        }

class HeaderFooterDetector:
    def __init__(self):
        self.repeating_headers = set()
        self.repeating_footers = set()
        
    def train(self, pages: List[Dict[str, Any]]):
        """ Huấn luyện tìm kiếm pattern lặp lại ở đầu và cuối trang """
        header_freq = {}
        footer_freq = {}
        total_pages = len(pages)
        if total_pages == 0:
            return
            
        for p in pages:
            lines = [l.strip() for l in p.get("text", "").split('\n') if l.strip()]
            if len(lines) > 0:
                header_freq[lines[0]] = header_freq.get(lines[0], 0) + 1
            if len(lines) > 1:
                header_freq[lines[1]] = header_freq.get(lines[1], 0) + 1
                
            if len(lines) > 0:
                footer_freq[lines[-1]] = footer_freq.get(lines[-1], 0) + 1
            if len(lines) > 1:
                footer_freq[lines[-2]] = footer_freq.get(lines[-2], 0) + 1
                
        # Ngưỡng lặp lại: Xuất hiện ở > 15% tổng số trang (đủ để kết luận là Header/Footer)
        threshold = max(2, int(total_pages * 0.15))
        self.repeating_headers = {k for k, v in header_freq.items() if v >= threshold}
        self.repeating_footers = {k for k, v in footer_freq.items() if v >= threshold}
        
    def is_header_footer(self, text: str, line_index: int, total_lines: int) -> bool:
        # 1. Bắt theo Vị trí + Mức độ lặp (Statistical Repetition)
        if line_index < 3 and text in self.repeating_headers:
            return True
        if line_index >= total_lines - 3 and text in self.repeating_footers:
            return True
            
        # 2. Bắt theo Pattern đặc thù doanh nghiệp
        lower_text = text.lower()
        if any(lower_text.startswith(k) or k in lower_text for k in ["mã số:", "lần ban hành:", "ngày ban hành", "ngày hiệu lực", "số trang:", "nội quy lao động", "masan", "consumer"]):
            if len(text.split()) < 12:
                return True
        if re.match(r"^\d+/\d+$", text) or re.match(r"^\d+$", text): # 28/32 hoặc 38
            return True
            
        return False

class GarbageDetector:
    def detect(self, text: str) -> Tuple[bool, float]:
        """ Không xóa rác, chỉ gắn cờ (Flagging) và điểm nghi ngờ """
        if bool(re.search(r'([a-zA-Z0-9\.\_\-])\1{5,}', text)): # EEEEEE hoặc ......
            return True, 0.8
        if len(text) > 5:
            special_chars = sum(1 for c in text if not c.isalnum() and not c.isspace())
            if special_chars / len(text) > 0.4:
                return True, 0.9
        return False, 0.0

class LineReconstructor:
    def __init__(self):
        self.is_structure_start = re.compile(
            r"^(?:(?:[IVXLCDM]+|\d+(?:\.\d+)*)[\.\:]|[a-zA-Z]\)|[-+*•]|Điều \d|Chương [IVXLCDM]|Phần [IVXLCDM]|Mục \d)"
        )
        
    def merge(self, raw_lines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        merged = []
        current = None
        for line_obj in raw_lines:
            text = line_obj["text"].strip()
            if not text: continue
            
            if current is None:
                current = {"text": text, "page": line_obj["page"]}
                continue
                
            prev_text = current["text"].strip()
            
            # Xử lý ngoại lệ OCR chia cắt số (2.4.) và chữ (Người lao động...) thành 2 dòng
            # Nếu dòng trước chỉ có số/chữ đơn độc, BẮT BUỘC gộp dòng tiếp theo
            is_orphan_number = bool(re.match(r"^(?:(?:[IVXLCDM]+|\d+(?:\.\d+)*)[\.\:]?|Điều \d+[\.\:\-]?)$", prev_text))
            
            starts_structured = bool(self.is_structure_start.match(text))
            prev_ends_with_punct = prev_text.endswith('.') or prev_text.endswith(':') or prev_text.endswith(';') or prev_text.endswith('!')
            starts_upper = text[0].isupper() if text else False
            
            should_merge = False
            if is_orphan_number:
                should_merge = True
            elif not starts_structured:
                if not prev_ends_with_punct:
                    should_merge = True
                elif not starts_upper:
                    should_merge = True
                    
            if should_merge:
                current["text"] += " " + text
            else:
                merged.append(current)
                current = {"text": text, "page": line_obj["page"]}
                
        if current:
            merged.append(current)
        return merged

class ListDetector:
    def __init__(self):
        self.bullet_pattern = re.compile(r"^[-+*•]\s+(.*)")
        self.alpha_pattern = re.compile(r"^[a-zA-Z]\)\s+(.*)")
        
    def detect(self, text: str) -> Tuple[bool, Optional[str], float]:
        if self.bullet_pattern.match(text):
            return True, "BULLET", 0.9
        if self.alpha_pattern.match(text):
            return True, "ALPHA", 0.85
        return False, None, 0.0

class HeadingDetector:
    def __init__(self):
        self.patterns = {
            HeadingType.PART: re.compile(r"(?i)^phần\s+[ivxlcdm\d]+[\.\:]?\s*(.*)"),
            HeadingType.CHAPTER: re.compile(r"(?i)^chương\s+[ivxlcdm\d]+[\.\:]?\s*(.*)"),
            HeadingType.ARTICLE: re.compile(r"(?i)^(?:điều|diều|điẽu|đieu)\s+\d+[\.\:\-]?\s*(.*)"),
            HeadingType.SECTION: re.compile(r"(?i)^mục\s+\d+[\.\:]?\s*(.*)"),
            HeadingType.NUMBERED: re.compile(r"^(?:[IVXLCDM]+|\d+(?:\.\d+)*)[\.\:]\s+(.*)")
        }

    def detect(self, text: str) -> Tuple[bool, Optional[HeadingType], int, float]:
        best_heading = None
        best_depth = -1
        base_confidence = 0.0
        
        for h_type, pattern in self.patterns.items():
            if pattern.match(text):
                best_heading = h_type
                if h_type in [HeadingType.PART, HeadingType.CHAPTER]:
                    best_depth = 1
                elif h_type in [HeadingType.ARTICLE, HeadingType.SECTION]:
                    best_depth = 2
                elif h_type == HeadingType.NUMBERED:
                    match_str = text.split()[0]
                    if re.match(r"^[IVXLCDM]+[\.\:]", match_str):
                        best_depth = 2
                    else:
                        best_depth = 2 + match_str.count('.')
                        
                word_count = len(text.split())
                length_score = 0.5 if word_count < 2 else max(0.0, 1.0 - (word_count / 30.0))
                
                if h_type == HeadingType.ARTICLE and word_count > 30:
                    length_score = -1.0 # Trích dẫn luật dài
                    
                base_confidence = 0.5 + (length_score * 0.5)
                break
                
        is_heading = best_heading is not None and base_confidence > 0.6
        
        # Nếu không đủ điểm tin cậy để làm Heading, phải xoá sạch dấu vết tránh lọt xuống dưới
        if not is_heading:
            best_heading = None
            best_depth = -1
            
        return is_heading, best_heading, best_depth, base_confidence


class BlockAnalyzer:
    """
    Pipeline phân tích Block v4: Multi-Signal & Pattern Learning
    """
    def __init__(self):
        self.header_footer_detector = HeaderFooterDetector()
        self.garbage_detector = GarbageDetector()
        self.line_reconstructor = LineReconstructor()
        self.heading_detector = HeadingDetector()
        self.list_detector = ListDetector()
        
    def analyze(self, pages: List[Dict[str, Any]]) -> List[StructureNode]:
        # 1. Huấn luyện (Train) Header/Footer Detector bằng tần suất xuất hiện
        self.header_footer_detector.train(pages)
        
        # 2. Extract & Filter Header/Footer
        filtered_lines = []
        for p in pages:
            if not p.get("text"): continue
            raw_lines = [l.strip() for l in p["text"].split('\n') if l.strip()]
            total = len(raw_lines)
            for i, line in enumerate(raw_lines):
                if not self.header_footer_detector.is_header_footer(line, i, total):
                    filtered_lines.append({"text": line, "page": p["page"]})
                    
        # 3. Line Merging
        merged = self.line_reconstructor.merge(filtered_lines)
        
        # 4. Classification Pipeline
        nodes = []
        for i, block in enumerate(merged):
            text = block["text"]
            block_type = BlockType.PARAGRAPH
            h_type, depth, classifier_conf = None, -1, 0.0
            list_type = None
            
            # Kiểm tra Rác
            is_garb, garb_conf = self.garbage_detector.detect(text)
            
            # Phân loại TOC
            lower_t = text.lower()
            if lower_t == "mục lục" or lower_t == "nội dung":
                block_type = BlockType.TOC
                classifier_conf = 0.95
            else:
                # Phân loại Heading vs List vs Paragraph
                is_list, l_type, l_conf = self.list_detector.detect(text)
                if is_list:
                    block_type = BlockType.LIST_ITEM
                    list_type = l_type
                    classifier_conf = l_conf
                else:
                    is_heading, h_type, depth, h_conf = self.heading_detector.detect(text)
                    if is_heading:
                        block_type = BlockType.HEADING
                        classifier_conf = h_conf
                    else:
                        # Paragraph
                        classifier_conf = 0.8
                        
            nodes.append(StructureNode(
                id=i + 1,
                text=text,
                block_type=block_type,
                heading_type=h_type,
                list_type=list_type,
                depth=depth,
                classifier_confidence=classifier_conf,
                is_garbage=is_garb,
                page=block["page"]
            ))
            
        return nodes
