import logging
from typing import Any, Dict, List

from sentence_transformers import CrossEncoder

from app.config import settings

logger = logging.getLogger(__name__)


class RerankerService:
    """Chấm lại cặp (câu hỏi, đoạn trích) bằng cross-encoder đa ngữ."""

    def __init__(self, model_name: str = settings.RERANKER_MODEL):
        self.model = None
        try:
            self.model = CrossEncoder(model_name)
            # Chạy thử để tokenizer/torch khởi tạo xong ngay lúc start, tránh
            # câu hỏi đầu tiên phải chờ cả chục giây.
            self.model.predict([("khởi động", "khởi động")], show_progress_bar=False)
            logger.info("Đã tải reranker: %s", model_name)
        except Exception as exc:  # thiếu mạng/model -> vẫn chạy bằng cosine
            logger.warning("Không tải được reranker (%s), dùng ngưỡng cosine.", exc)

    @property
    def enabled(self) -> bool:
        return self.model is not None

    def rerank(self, query: str, hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not self.enabled or not hits:
            return hits
        pairs = [
            (query, hit["content"][: settings.RERANK_PASSAGE_CHARS])
            for hit in hits
        ]
        scores = self.model.predict(pairs, show_progress_bar=False)
        for hit, score in zip(hits, scores):
            hit["rerank_score"] = round(float(score), 4)
        return sorted(hits, key=lambda hit: hit["rerank_score"], reverse=True)

    def score_pairs(self, query: str, texts: List[str]) -> List[float]:
        """Chấm từng đoạn ngắn (câu/cụm câu) thay vì cả chunk dài nhiễu OCR."""
        if not self.enabled or not texts:
            return []
        pairs = [(query, text) for text in texts]
        scores = self.model.predict(pairs, show_progress_bar=False)
        return [round(float(score), 4) for score in scores]
