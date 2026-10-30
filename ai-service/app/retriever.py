from typing import List, Dict, Any, Optional
import logging
import re
from pathlib import Path
import json
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.embedding_service import EmbeddingService, fold_text
from app.qdrant_service import QdrantService

logger = logging.getLogger(__name__)

# Rerank hybrid: giữ độ nhớ nhúng (vector) nhưng tăng hạng cho đoạn khớp từ khóa.
# OCR tiếng Việt hay làm hỏng dấu nên việc khớp từ sau khi fold rất hiệu quả.
LEXICAL_WEIGHT = 0.3


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
                if score < min_score:
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
                # Giữ nguyên vector_score để bộ fallback còn so với ngưỡng 0.3.
                lexical = lexical_score(query, content)
                combined = score + LEXICAL_WEIGHT * lexical
                results.append({
                    "score": round(combined, 4),
                    "vector_score": round(score, 4),
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
        return results[:top_k]
