from typing import List, Dict, Any, Union
import logging
from sentence_transformers import SentenceTransformer
from app.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    Module M3.1: Embedding Service
    Sử dụng mô hình SentenceTransformer đa ngôn ngữ để mã hóa văn bản thành vector.
    """
    def __init__(self, model_name: str = settings.EMBEDDING_MODEL):
        self.model_name = model_name
        logger.info(f"Đang tải Embedding Model: {self.model_name}")
        self.model = SentenceTransformer(self.model_name)
        if hasattr(self.model, "get_embedding_dimension"):
            self.vector_dim = self.model.get_embedding_dimension()
        else:
            self.vector_dim = self.model.get_sentence_embedding_dimension()
        logger.info(f"Đã khởi tạo Embedding Model thành công (Kích thước: {self.vector_dim} chiều)")

    def embed_query(self, query: str) -> List[float]:
        """
        Nhúng 1 câu hỏi từ người dùng thành vector phục vụ tìm kiếm.
        """
        if not query or not query.strip():
            return [0.0] * self.vector_dim
            
        vector = self.model.encode(query.strip(), convert_to_numpy=True)
        return vector.tolist()

    def embed_documents(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Nhúng danh sách văn bản theo batch.
        """
        if not texts:
            return []
            
        cleaned_texts = [t.strip() if t else "" for t in texts]
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
