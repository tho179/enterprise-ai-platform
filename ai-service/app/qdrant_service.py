from typing import List, Dict, Any, Optional
import uuid
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)
from app.config import settings

logger = logging.getLogger(__name__)

class QdrantService:
    """
    Module M3.2: Qdrant Integration
    Quản lý kết nối, khởi tạo Collection và lưu trữ Vector + Metadata Payload.
    """
    def __init__(
        self,
        url: str = settings.QDRANT_URL,
        collection_name: str = settings.QDRANT_COLLECTION,
        local_path: Optional[str] = None
    ):
        self.collection_name = collection_name
        self.url = url
        
        # Kết nối tới Qdrant Server (trong Docker) hoặc fallback sang local disk nếu cần
        if local_path:
            logger.info(f"Khởi tạo Qdrant Local Storage tại: {local_path}")
            self.client = QdrantClient(path=local_path)
        else:
            logger.info(f"Kết nối tới Qdrant Server: {self.url}")
            self.client = QdrantClient(url=self.url)

    def create_collection_if_not_exists(self, vector_size: int = 384):
        """ Khởi tạo collection nếu chưa có trên Qdrant """
        try:
            collections = [c.name for c in self.client.get_collections().collections]
            if self.collection_name not in collections:
                logger.info(f"Tạo collection '{self.collection_name}' (dim={vector_size}, metric=Cosine)")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
            else:
                logger.info(f"Collection '{self.collection_name}' đã tồn tại.")
        except Exception as e:
            logger.error(f"Lỗi khi kiểm tra/tạo collection Qdrant: {e}")
            raise e

    def upsert_chunks(self, embedded_chunks: List[Dict[str, Any]], batch_size: int = 64) -> int:
        """ Nạp danh sách chunk kèm vector và metadata vào Qdrant """
        if not embedded_chunks:
            return 0
            
        vector_dim = len(embedded_chunks[0]["vector"])
        self.create_collection_if_not_exists(vector_size=vector_dim)

        total_upserted = 0
        batch_points = []

        for i, chunk in enumerate(embedded_chunks, 1):
            chunk_id_str = chunk.get("chunk_id", f"CHUNK-{i}")
            # Sinh UUID chuẩn từ chunk_id để đảm bảo idempotency (không bị trùng lặp khi chạy lại)
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id_str))
            
            payload = {
                "chunk_id": chunk_id_str,
                "content": chunk.get("content", ""),
                **(chunk.get("metadata", {}))
            }
            
            point = PointStruct(
                id=point_id,
                vector=chunk["vector"],
                payload=payload
            )
            batch_points.append(point)

            if len(batch_points) >= batch_size:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch_points
                )
                total_upserted += len(batch_points)
                batch_points = []

        if batch_points:
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch_points
            )
            total_upserted += len(batch_points)

        logger.info(f"Đã upsert thành công {total_upserted} chunks vào Qdrant collection '{self.collection_name}'")
        return total_upserted

    def count(self) -> int:
        """ Đếm tổng số vector points hiện có trong collection """
        res = self.client.count(collection_name=self.collection_name)
        return res.count
