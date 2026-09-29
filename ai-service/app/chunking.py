import re # cắt nhỏ
from dataclasses import asdict, dataclass # đóng gói
from typing import List, Dict, Any # dán nhãn

@dataclass
class TextChunk:
    chunk_index: int
    content: str
    start_char: int
    end_char: int
    metadata: Dict[str, Any] = None
    
    # start,end_char dùng để sau này hightlight khi trả về kết quả


class TextChunker:
    def __init__(
        self,
        chunk_size: int = 1200,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
        ):
            if chunk_size <= 0:
                raise ValueError("chunk_size phải lớn hơn 0")
            if chunk_overlap < 0:
                raise ValueError("chunk_overlap không được âm")
            if chunk_overlap >= chunk_size:
                raise ValueError("chunk_overlap phải nhỏ hơn chunk_size")
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap
            self.min_chunk_size = min_chunk_size
    
    def chunk_blocks(self, blocks: List[Dict[str, Any]]) -> List[TextChunk]:
        """
        Nhận đầu vào là mảng blocks từ BlockAnalyzer.
        Cắt nhỏ nội dung từng block và gán lại toàn bộ thông tin phân cấp (metadata).
        """
        all_chunks = []
        for block in blocks:
            text = block.get("content", "")
            if not text.strip():
                continue
                
            # Trích xuất metadata của block
            metadata = {
                "block_id": block.get("block_id"),
                "parent_chapter": block.get("parent_chapter", ""),
                "parent_section": block.get("parent_section", ""),
                "title": block.get("title", ""),
                "label": block.get("label", "")
            }
            
            # Cắt text của block này
            chunks = self.split_text(text)
            
            # Gắn metadata vào từng mảnh cắt được
            for c in chunks:
                c.metadata = metadata
                c.chunk_index = len(all_chunks) + 1
                all_chunks.append(c)
                
        return all_chunks

    def split_text(self, text: str) -> List[TextChunk]:
        """
        Chia văn bản thành các chunk có overlap.

        Ưu tiên giữ đoạn văn và câu.
        """
        if not text or not text.strip():
            return []

        normalized_text = self._normalize_text(text)

        paragraphs = self._split_into_paragraphs(normalized_text)

        chunks: List[TextChunk] = []
        current_text = ""
        current_start = 0
        current_position = 0

        for paragraph in paragraphs:
            paragraph = paragraph.strip()

            if not paragraph:
                continue

            # Nếu thêm đoạn mới vẫn nằm trong giới hạn chunk
            candidate = (
                paragraph
                if not current_text
                else current_text + "\n\n" + paragraph
            )

            if len(candidate) <= self.chunk_size:
                if not current_text:
                    current_start = current_position

                current_text = candidate
                current_position += len(paragraph) + 2
                continue

            # Lưu chunk hiện tại trước
            if current_text.strip():
                chunks.append(
                    self._create_chunk(
                        index=len(chunks),
                        content=current_text,
                        start_char=current_start,
                    )
                )

            # Nếu đoạn mới không quá dài, bắt đầu chunk mới
            if len(paragraph) <= self.chunk_size:
                overlap_text = self._get_overlap(current_text)

                if overlap_text:
                    current_text = (
                        overlap_text
                        + "\n\n"
                        + paragraph
                    )
                else:
                    current_text = paragraph

                current_start = max(
                    0,
                    current_position - len(overlap_text),
                )

                current_position += len(paragraph) + 2
            else:
                # Đoạn quá dài thì chia nhỏ theo câu
                paragraph_chunks = self._split_long_text(paragraph)

                for small_chunk in paragraph_chunks:
                    if current_text.strip():
                        chunks.append(
                            self._create_chunk(
                                index=len(chunks),
                                content=current_text,
                                start_char=current_start,
                            )
                        )

                    current_text = small_chunk
                    current_start = current_position
                    current_position += len(small_chunk)

        # Lưu chunk cuối cùng
        if current_text.strip():
            chunks.append(
                self._create_chunk(
                    index=len(chunks),
                    content=current_text,
                    start_char=current_start,
                )
            )

        return [
            chunk
            for chunk in chunks
            if len(chunk.content.strip()) >= self.min_chunk_size
        ]

    def _normalize_text(self, text: str) -> str:
        """
        Chuẩn hóa khoảng trắng nhưng vẫn giữ xuống dòng giữa các đoạn.
        """

        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        # Giảm nhiều khoảng trắng liên tiếp
        text = re.sub(r"[ \t]+", " ", text)

        # Giảm quá nhiều dòng trống
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def _split_into_paragraphs(self, text: str) -> List[str]:
        """
        Chia văn bản theo các đoạn được ngăn bởi dòng trống.
        """

        return re.split(r"\n\s*\n", text)

    def _split_long_text(self, text: str) -> List[str]:
        """
        Chia đoạn quá dài theo câu.
        Nếu câu vẫn quá dài thì cắt theo ký tự.
        """

        sentences = re.split(
            r"(?<=[.!?。！？])\s+",
            text,
        )

        result: List[str] = []
        current = ""

        for sentence in sentences:
            sentence = sentence.strip()

            if not sentence:
                continue

            candidate = (
                sentence
                if not current
                else current + " " + sentence
            )

            if len(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    result.append(current)

                if len(sentence) <= self.chunk_size:
                    current = sentence
                else:
                    # Câu quá dài, cắt cứng theo chunk_size
                    for start in range(
                        0,
                        len(sentence),
                        self.chunk_size - self.chunk_overlap,
                    ):
                        part = sentence[
                            start:start + self.chunk_size
                        ]

                        if part.strip():
                            result.append(part)

                    current = ""

        if current:
            result.append(current)

        return result

    def _get_overlap(self, text: str) -> str:
        """
        Lấy phần cuối của chunk trước để làm overlap.
        """

        if not text:
            return ""

        return text[-self.chunk_overlap:]

    def _create_chunk(
        self,
        index: int,
        content: str,
        start_char: int,
    ) -> TextChunk:
        content = content.strip()

        return TextChunk(
            chunk_index=index,
            content=content,
            start_char=start_char,
            end_char=start_char + len(content),
        )
    

    
