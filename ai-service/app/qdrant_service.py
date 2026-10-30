from typing import List, Dict, Any, Optional
import uuid
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams,
    Distance,
    PointStruct,
    Filter,
    FilterSelector,
    FieldCondition,
    MatchValue
)
from app.config import settings

logger = logging.getLogger(__name__)

class QdrantService:
    """
    Module M3.2: Qdrant Integration
    Manages connection, collection initialization, and storage of vectors and metadata.
    """
    def __init__(
        self,
        url: str = settings.QDRANT_URL,
        collection_name: str = settings.QDRANT_COLLECTION,
        local_path: Optional[str] = None
    ):
        self.collection_name = collection_name
        self.url = url
        
        # Connect to remote Qdrant server or fallback to local disk storage
        if local_path:
            logger.info(f"Initializing Qdrant Local Storage at: {local_path}")
            self.client = QdrantClient(path=local_path)
        else:
            try:
                logger.info(f"Connecting to Qdrant Server at: {self.url}")
                client = QdrantClient(url=self.url, timeout=2.0)
                client.get_collections()
                self.client = client
            except Exception as exc:
                fallback_path = settings.QDRANT_STORAGE_PATH or "data/qdrant_storage"
                logger.warning(
                    f"Could not connect to Qdrant server at {self.url} ({exc}). "
                    f"Falling back to local disk storage at '{fallback_path}'."
                )
                self.client = QdrantClient(path=fallback_path)

    def create_collection_if_not_exists(self, vector_size: int = 384):
        """Initialize collection if it does not exist in Qdrant."""
        try:
            collections = [c.name for c in self.client.get_collections().collections]
            if self.collection_name not in collections:
                logger.info(f"Creating collection '{self.collection_name}' (dim={vector_size}, metric=Cosine)")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
            else:
                logger.info(f"Collection '{self.collection_name}' already exists.")
        except Exception as e:
            logger.error(f"Error checking/creating Qdrant collection: {e}")
            raise e

    def upsert_chunks(self, embedded_chunks: List[Dict[str, Any]], batch_size: int = 64) -> int:
        """Ingest chunk list with vectors and metadata into Qdrant."""
        if not embedded_chunks:
            return 0
            
        vector_dim = len(embedded_chunks[0]["vector"])
        self.create_collection_if_not_exists(vector_size=vector_dim)

        total_upserted = 0
        batch_points = []

        for i, chunk in enumerate(embedded_chunks, 1):
            chunk_id_str = chunk.get("chunk_id", f"CHUNK-{i}")
            # Generate deterministic UUID to ensure idempotency across re-runs
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

        logger.info(f"Successfully upserted {total_upserted} chunks into Qdrant collection '{self.collection_name}'")
        return total_upserted

    def count(self) -> int:
        """Count total vector points in collection, returning 0 on error or if empty."""
        try:
            res = self.client.count(collection_name=self.collection_name)
            return res.count
        except Exception:
            return 0

    def delete_by_document_id(self, document_id: str, version_id: Optional[str] = None) -> int:
        """Delete all vectors for a document (optionally limited to one version)."""
        try:
            collections = [c.name for c in self.client.get_collections().collections]
            if self.collection_name not in collections:
                return 0
            must_conditions = [
                FieldCondition(
                    key="document_id",
                    match=MatchValue(value=document_id)
                )
            ]
            if version_id:
                must_conditions.append(
                    FieldCondition(
                        key="version_id",
                        match=MatchValue(value=version_id)
                    )
                )
            before = self.count()
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=FilterSelector(
                    filter=Filter(must=must_conditions)
                )
            )
            deleted = before - self.count()
            scope = f"document {document_id}" + (f" version {version_id}" if version_id else "")
            logger.info(f"Deleted {deleted} vectors for {scope}")
            return deleted
        except Exception as exc:
            logger.error(f"Error deleting vectors for document {document_id}: {exc}")
            return 0
