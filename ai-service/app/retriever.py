from typing import List, Dict, Any, Optional
import logging
import re
from pathlib import Path
import json
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.config import settings
from app.embedding_service import EmbeddingService, fold_text
from app.qdrant_service import QdrantService
from app.reranker_service import RerankerService

logger = logging.getLogger(__name__)

# Rerank hybrid: giữ độ nhớ nhúng (vector) nhưng tăng hạng cho đoạn khớp từ khóa.
# OCR tiếng Việt hay làm hỏng dấu nên việc khớp từ sau khi fold rất hiệu quả.
LEXICAL_WEIGHT = 0.3
# Câu hỏi dạng "Điều 43 quy định gì?" gần như không có tín hiệu ngữ nghĩa
# (số điều không được embedding tốt) -> ưu tiên mạnh đoạn chứa đúng số điều.
ARTICLE_BOOST = 0.45
ARTICLE_PATTERN = re.compile(r"\bdieu\s+(\d{1,3})\b")


def _article_numbers(query: str) -> set:
    return set(ARTICLE_PATTERN.findall(fold_text(query)))


def lexical_score(query: str, content: str) -> float:
    """Tỷ lệ từ khóa của câu hỏi xuất hiện trong nội dung (sau khi bỏ dấu)."""
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0.0
    content_tokens = set(_tokens(content))
    hits = sum(1 for token in query_tokens if token in content_tokens)
    return hits / len(query_tokens)


def _tokens(text: str) -> List[str]:
    seen = set()
    out = []
    for token in re.findall(r"[a-z0-9]{2,}", fold_text(text)):
        if token not in seen:
            seen.add(token)
            out.append(token)
    return out


class VectorRetriever:
    """
    Module M3.3: Vector Retriever
    Embeds query into vector and queries Top-K most similar chunks from Qdrant.
    """
    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        qdrant_service: Optional[QdrantService] = None
    ):
        self.embedding = embedding_service or EmbeddingService()
        self.qdrant = qdrant_service or QdrantService()
        self.reranker = RerankerService()
        self._ensure_bootstrap()

    def _ensure_bootstrap(self):
        """Auto-seed debug chunks if collection is empty and debug dataset exists."""
        try:
            if self.qdrant.count() == 0:
                for candidate in [
                    Path("debug/06_embedded_chunks.json"),
                    Path("ai-service/debug/06_embedded_chunks.json"),
                    Path("../debug/06_embedded_chunks.json"),
                ]:
                    if candidate.exists():
                        chunks = json.loads(candidate.read_text(encoding="utf-8"))
                        self.qdrant.upsert_chunks(chunks)
                        logger.info("Auto-seeded Qdrant collection with precomputed debug chunks.")
                        break
        except Exception as exc:
            logger.warning(f"Auto-seed check skipped or failed: {exc}")

    def search(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
        min_score: float = 0.35
    ) -> List[Dict[str, Any]]:
        """
        Search for document chunks with highest semantic similarity score.
        """
        if not query or not query.strip():
            return []

        # 1. Embed query into vector
        query_vector = self.embedding.embed_query(query)
        seen_keys: set = set()
        article_numbers = _article_numbers(query)

        # 2. Build metadata filter if specified
        query_filter = None
        if document_id:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            )

        # 3. Query Qdrant for nearest points
        # Tìm sâu (oversample): cosine của model nhỏ cụm sát nhau nên đoạn đích
        # có thể nằm ngoài top tìm kiếm thường — phải nạp đủ sâu rồi rerank lexical.
        results = []
        try:
            fetch_limit = min(200, max(top_k * 10, 100))
            if hasattr(self.qdrant.client, "search"):
                hits = self.qdrant.client.search(
                    collection_name=self.qdrant.collection_name,
                    query_vector=query_vector,
                    query_filter=query_filter,
                    limit=fetch_limit
                )
            else:
                response = self.qdrant.client.query_points(
                    collection_name=self.qdrant.collection_name,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=fetch_limit
                )
                hits = response.points

            for hit in hits:
                score = getattr(hit, "score", 0.0)
                # Câu hỏi có số điều ("Điều 43") có cosine gốc rất thấp nên không
                # được lọc thô trước rerank, nếu không chunk đúng bị loại mất.
                if score < min_score and not article_numbers:
                    continue

                payload = getattr(hit, "payload", {}) or {}
                content = payload.get("content", "")

                # Chống trùng lặp: 1 tài liệu nhiều phiên bản (hoặc chunk có
                # vùng overlap) cho ra điểm y hệt nhau và chiếm Top-K. Giữ hit đầu.
                dedup_key = (payload.get("page_start"), content)
                if dedup_key in seen_keys:
                    continue
                seen_keys.add(dedup_key)

                # Hybrid rerank: điểm cuối = cosine + trọng số × overlap từ khóa.
                # Giữ nguyên vector_score để bộ fallback còn so với ngưỡng tin cậy.
                lexical = lexical_score(query, content)
                folded_content = fold_text(content)
                article_match = any(
                    re.search(rf"\bdieu\s+{number}\b", folded_content)
                    for number in article_numbers
                )
                combined = score + LEXICAL_WEIGHT * lexical
                if article_match:
                    combined += ARTICLE_BOOST
                results.append({
                    "score": round(combined, 4),
                    "vector_score": round(score, 4),
                    "article_match": article_match,
                    "chunk_id": payload.get("chunk_id"),
                    "content": content,
                    "metadata": {
                        "document_id": payload.get("document_id"),
                        "page_start": payload.get("page_start"),
                        "page_end": payload.get("page_end"),
                        "section_path": payload.get("section_path", []),
                        "document_type": payload.get("document_type")
                    }
                })
        except Exception as e:
            logger.error(f"Error during vector search in Qdrant: {e}")
            raise e

        if not results:
            logger.info("No vector hits for query (min_score=%s)", min_score)
            return results
        results.sort(key=lambda r: r["score"], reverse=True)

        # Cross-encoder chấm lại nhóm đầu: sửa thứ hạng sai và cung cấp điểm
        # tin cậy cho bước quyết định trả lời/từ chối.
        head = results[: settings.RERANK_CANDIDATES]
        if self.reranker.enabled and head:
            head = self.reranker.rerank(query, head)
            results = head + results[settings.RERANK_CANDIDATES:]
        return results[:top_k]
