import re
from dataclasses import dataclass, asdict
from typing import List, Dict, Any

@dataclass
class TextChunk:
    chunk_index: int
    content: str
    metadata: Dict[str, Any]

class AdaptiveChunker:
    """
    Adaptive Chunking Pipeline:
    1. Structure-aware: Gom nhóm theo section_path (Cùng một Điều/Khoản sẽ nằm chung 1 chunk).
    2. Paragraph-aware: Nếu Điều khoản đó quá dài, cắt theo đoạn văn.
    3. Sentence-aware: Nếu 1 đoạn văn lỡ viết quá dài không xuống dòng, cắt theo câu.
    4. Character-aware: Nếu 1 câu quá dài (rất hiếm), cắt cứng theo số lượng ký tự có Overlap.
    """
    def __init__(
        self,
        chunk_size: int = 1200,
        chunk_overlap: int = 200,
        min_chunk_size: int = 50,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_heading_chars = 200

    PREAMBLE_TITLE = "Phần mở đầu"

    def chunk_nodes(self, nodes: List[Dict[str, Any]]) -> List[TextChunk]:
        all_chunks = []
        current_group_text = []
        current_pages = []
        current_section_path = None
        self._section_type = None

        for node in nodes:
            # LỌC RÁC & MỤC LỤC: Không đưa vào RAG
            if node.get("block_type") == "TOC" or node.get("is_garbage"):
                continue
                
            text = node.get("text", "").strip()
            if not text:
                continue
                
            section_path = list(node.get("section_path") or [])
            # Text before the first heading (cover, preamble) still gets a path,
            # so every chunk can be cited with a location.
            if not section_path:
                section_path = [self.PREAMBLE_TITLE]
            page = node.get("page", 1)

            # NGUYÊN TẮC 1: STRUCTURE-AWARE (Gom theo section_path)
            # Nếu node này thuộc về một mục khác (khác section_path) -> Đóng gói khối hiện tại
            if current_group_text and section_path != current_section_path:
                self._flush_group(current_group_text, current_section_path, current_pages, all_chunks)
                current_group_text = []
                current_pages = []

            current_section_path = section_path
            self._section_type = node.get("section_type") or (
                "PREAMBLE" if section_path == [self.PREAMBLE_TITLE] else "SECTION"
            )
            current_group_text.append(text)
            current_pages.append(page)
            
            # Kiểm tra kích thước đang gom.
            # Nếu dồn lại đã bắt đầu vượt chunk_size -> Đóng gói khối hiện tại sớm để tránh bị đầy quá
            temp_len = sum(len(t) for t in current_group_text) + (len(current_group_text) - 1) * 2
            if temp_len >= self.chunk_size:
                self._flush_group(current_group_text, current_section_path, current_pages, all_chunks)
                current_group_text = []
                current_pages = []

        # Xử lý đoạn cuối cùng còn sót lại
        if current_group_text:
            self._flush_group(current_group_text, current_section_path, current_pages, all_chunks)

        # Lọc bỏ các chunk quá ngắn không mang lại ngữ nghĩa
        return [c for c in all_chunks if len(c.content.strip()) >= self.min_chunk_size]

    def _flush_group(self, group_text_list: List[str], section_path: Any, pages: List[int], all_chunks: List[TextChunk]):
        """ Đóng gói một nhóm văn bản cùng section_path. Nếu quá dài, tự động kích hoạt Fallback. """
        merged_text = "\n\n".join(group_text_list)
        sub_chunks = self._fallback_split(merged_text)
        
        page_start = min(pages) if pages else 1
        page_end = max(pages) if pages else page_start
        metadata = {
            "section_path": section_path if section_path else [],
            "section_type": self._section_type or "SECTION",
            "page_start": page_start,
            "page_end": page_end
        }
        
        for sc in sub_chunks:
            all_chunks.append(TextChunk(
                chunk_index=len(all_chunks) + 1,
                content=sc,
                metadata=metadata.copy()
            ))

    def _fallback_split(self, text: str) -> List[str]:
        """ NGUYÊN TẮC 2: PARAGRAPH-AWARE """
        if not text or not text.strip():
            return []
            
        if len(text) <= self.chunk_size:
            return [text.strip()]
            
        chunks = []
        paragraphs = re.split(r'\n\s*\n', text)
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para: continue
            
            candidate = current_chunk + ("\n\n" if current_chunk else "") + para
            
            if len(candidate) <= self.chunk_size:
                current_chunk = candidate
            else:
                # Tiêu đề ngắn phải đi cùng nội dung, không thành chunk rỗng nghĩa.
                if len(para) > self.chunk_size and 0 < len(current_chunk) < self.max_heading_chars:
                    para = current_chunk + " " + para
                    current_chunk = ""
                if current_chunk:
                    chunks.append(current_chunk)

                if len(para) > self.chunk_size:
                    # Đoạn văn quá dài, kích hoạt Fallback cấp 3: Sentence-aware
                    sentence_chunks = self._sentence_split(para)
                    for sc in sentence_chunks[:-1]:
                        chunks.append(sc)
                    current_chunk = sentence_chunks[-1] if sentence_chunks else ""
                else:
                    overlap = current_chunk[-self.chunk_overlap:] if current_chunk else ""
                    current_chunk = (overlap + "\n\n" if overlap else "") + para
                    
        if current_chunk:
            chunks.append(current_chunk)
            
        return [c.strip() for c in chunks if c.strip()]

    _OUTLINE_NUMBER = re.compile(r"^(?:\d+(?:\.\d+)*|[IVXLCDM]+|[a-z])\.$")

    def _split_sentences(self, text: str) -> List[str]:
        """Split at sentence ends, but keep outline numbers ("1.", "1.1.", "II.")
        attached to the clause they introduce."""
        parts = [p for p in re.split(r"(?<=[.!?。！？])\s+", text or "") if p.strip()]
        sentences: List[str] = []
        carry = ""
        for part in parts:
            part = part.strip()
            if self._OUTLINE_NUMBER.match(part):
                carry = f"{carry} {part}".strip()
                continue
            # "...rõ ràng. 1.1. Phạm vi" splits as "1.1." + "Phạm vi"; the
            # number ends the previous piece when it was split mid-token.
            tail = re.search(r"\s((?:\d+(?:\.\d+)*|[IVXLCDM]+)\.)$", part)
            if tail and not carry:
                sentences.append(part[: tail.start()].strip())
                carry = tail.group(1)
                continue
            sentences.append(f"{carry} {part}".strip() if carry else part)
            carry = ""
        if carry:
            sentences.append(carry)
        return [s for s in sentences if s]

    def _sentence_split(self, text: str) -> List[str]:
        """ NGUYÊN TẮC 3: SENTENCE-AWARE """
        sentences = self._split_sentences(text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence: continue
            
            candidate = current_chunk + (" " if current_chunk else "") + sentence
            
            if len(candidate) <= self.chunk_size:
                current_chunk = candidate
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                    
                if len(sentence) > self.chunk_size:
                    # Kích hoạt Fallback cấp 4 (Cuối cùng): Character/Token Fallback
                    char_chunks = self._character_split(sentence)
                    for cc in char_chunks[:-1]:
                        chunks.append(cc)
                    current_chunk = char_chunks[-1] if char_chunks else ""
                else:
                    overlap = current_chunk[-self.chunk_overlap:] if current_chunk else ""
                    current_chunk = (overlap + " " if overlap else "") + sentence
                    
        if current_chunk:
            chunks.append(current_chunk)
            
        return [c.strip() for c in chunks if c.strip()]
        
    def _character_split(self, text: str) -> List[str]:
        """ NGUYÊN TẮC 4: CHARACTER-AWARE (Chặt cứng, bắt buộc phải có để chống lỗi) """
        chunks = []
        start = 0
        while start < len(text):
            chunks.append(text[start:start + self.chunk_size])
            start += self.chunk_size - self.chunk_overlap
        return chunks
