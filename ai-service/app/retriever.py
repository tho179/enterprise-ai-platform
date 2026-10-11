from typing import List, Dict, Any, Optional
import logging
from qdrant_client.models import Filter, FieldCondition, MatchValue

from app.embedding_service import EmbeddingService
from app.qdrant_service import QdrantService

logger = logging.getLogger(__name__)

class VectorRetriever:
    """
    Module M3.3: Vector Retriever
    Chuyển câu hỏi thành vector và truy vấn Top-K chunks tương đồng nhất từ Qdrant.
    """
    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        qdrant_service: Optional[QdrantService] = None
    ):
        self.embedding = embedding_service or EmbeddingService()
        self.qdrant = qdrant_service or QdrantService()

    def search(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
        min_score: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Tìm kiếm các đoạn văn bản có độ tương đồng ngữ nghĩa cao nhất.
        """
        if not query or not query.strip():
            return []

        # 1. Nhúng câu hỏi thành vector
        query_vector = self.embedding.embed_query(query)

        # 2. Xây dựng bộ lọc Metadata nếu có
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

        # 3. Tìm kiếm trong Qdrant
        # qdrant-client hỗ trợ client.search hoặc client.query_points
        results = []
        try:
            if hasattr(self.qdrant.client, "search"):
                hits = self.qdrant.client.search(
                    collection_name=self.qdrant.collection_name,
                    query_vector=query_vector,
                    query_filter=query_filter,
                    limit=top_k
                )
            else:
                response = self.qdrant.client.query_points(
                    collection_name=self.qdrant.collection_name,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=top_k
                )
                hits = response.points

            for hit in hits:
                score = getattr(hit, "score", 0.0)
                if score < min_score:
                    continue

                payload = getattr(hit, "payload", {}) or {}
                results.append({
                    "score": round(score, 4),
                    "chunk_id": payload.get("chunk_id"),
                    "content": payload.get("content", ""),
                    "metadata": {
                        "document_id": payload.get("document_id"),
                        "page_start": payload.get("page_start"),
                        "page_end": payload.get("page_end"),
                        "section_path": payload.get("section_path", []),
                        "document_type": payload.get("document_type")
                    }
                })
        except Exception as e:
            logger.error(f"Lỗi khi tìm kiếm vector trong Qdrant: {e}")
            raise e

        return results
