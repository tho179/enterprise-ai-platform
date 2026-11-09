from typing import List, Dict, Any, Union
import logging
import re
import unicodedata
from app.config import settings

logger = logging.getLogger(__name__)


def fold_text(text: str) -> str:
    """
    Chuẩn hóa văn bản trước khi nhúng: bỏ dấu tiếng Việt (ổ -> o, đ -> d),
    hạ chữ thường, nén khoảng trắng. OCR tiếng Việt hay mất/nhầm dấu nên
    fold cả truy vấn lẫn tài liệu giúp độ tương đồng ổn định hơn hẳn.
    """
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    stripped = stripped.replace("\u0111", "d").replace("\u0110", "D")
    return re.sub(r"\s+", " ", stripped.casefold()).strip()


class EmbeddingService:
    """
    Module M3.1: Embedding Service
    Sử dụng mô hình SentenceTransformer đa ngôn ngữ để mã hóa văn bản thành vector.
    """
    def __init__(self, model_name: str = settings.EMBEDDING_MODEL):
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.query_prefix = settings.EMBEDDING_QUERY_PREFIX
        self.passage_prefix = settings.EMBEDDING_PASSAGE_PREFIX
        logger.info(f"Đang tải Embedding Model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        if hasattr(self.model, "get_embedding_dimension"):
            self.vector_dim = self.model.get_embedding_dimension()
        else:
            self.vector_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Đã khởi tạo Embedding Model thành công (Kích thước: {self.vector_dim} chiều)")

    def _prepare(self, text: str, prefix: str) -> str:
        # Giữ dấu: đo trên bộ nhãn (docs/evaluation_graphrag.md) cho thấy bỏ dấu
        # làm E5 mất phần lớn tín hiệu tiếng Việt. fold_text chỉ dùng khớp từ khóa.
        prepared = fold_text(text) if settings.EMBEDDING_FOLD_TEXT else " ".join(text.split())
        return f"{prefix}{prepared}" if prefix else prepared

    def embed_query(self, query: str) -> List[float]:
        """
        Nhúng 1 câu hỏi từ người dùng thành vector phục vụ tìm kiếm.
        """
        if not query or not query.strip():
            return [0.0] * self.vector_dim

        vector = self.model.encode(
            self._prepare(query, self.query_prefix),
            convert_to_numpy=True,
        )
        return vector.tolist()

    def embed_documents(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Nhúng danh sách văn bản theo batch.
        """
        if not texts:
            return []

        cleaned_texts = [self._prepare(t, self.passage_prefix) for t in texts]
        vectors = self.model.encode(
            cleaned_texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True
        )
        return vectors.tolist()

    def embed_chunks(self, chunks: List[Dict[str, Any]], batch_size: int = 32) -> List[Dict[str, Any]]:
        """
        Nhúng trực tiếp danh sách chunks từ Bước M2 (05_enriched_chunks.json)
        và bổ sung trường 'vector' vào mỗi chunk.
        """
        if not chunks:
            return []

        texts = [c.get("content", "") for c in chunks]
        vectors = self.embed_documents(texts, batch_size=batch_size)

        embedded_chunks = []
        for chunk, vector in zip(chunks, vectors):
            new_chunk = chunk.copy()
            new_chunk["vector"] = vector
            embedded_chunks.append(new_chunk)

        return embedded_chunks
