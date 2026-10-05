from typing import List, Dict, Any
from dataclasses import asdict
import uuid

class MetadataEnricher:
    def __init__(
        self,
        document_id: str,
        version_id: str = "VER-001",
        document_type: str = "regulation",
        language: str = "vi",
        is_current: bool = True
    ):
        """
        Nhận các thông tin nghiệp vụ từ hệ thống quản lý Document (vd: Spring Boot)
        để bơm vào các chunk trước khi đưa sang Qdrant/Neo4j.
        """
        self.document_id = document_id
        self.version_id = version_id
        self.document_type = document_type
        self.language = language
        self.is_current = is_current

    def enrich(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        enriched_chunks = []
        for i, chunk in enumerate(chunks, 1):
            # Format chunk_id chuẩn: DOC-001-CHUNK-0001
            chunk_id = f"{self.document_id}-CHUNK-{i:04d}"
            
            content = chunk.get("content", "")
            
            # Kế thừa metadata từ Chunker
            base_meta = chunk.get("metadata", {})
            
            # Gộp và cấu trúc lại Metadata hoàn chỉnh
            enriched_metadata = {
                # Nhóm A - Bắt buộc (Định danh & Phả hệ)
                "document_id": self.document_id,
                "version_id": self.version_id,
                "page_start": base_meta.get("page_start", 1),
                "page_end": base_meta.get("page_end", 1),
                "section_path": base_meta.get("section_path", []),
                "section_type": base_meta.get("section_type"),
                "chunk_type": base_meta.get("chunk_type", "text"),
                "is_current": self.is_current,
                
                # Nhóm B - Phục vụ RAG
                "document_type": self.document_type,
                "language": self.language,
                "char_count": len(content),
                # token_count tạm thời tính nháp (1 token ~ 4 chars). Sẽ update sau khi chọn Model.
                "token_count": len(content) // 4,
                
                # Nhóm C - Phục vụ Enterprise/RBAC (Có thể pass null, chờ DB update)
                "access_level": None,
                "allowed_roles": []
            }

            enriched_chunk = {
                "chunk_id": chunk_id,
                "content": content,
                "metadata": enriched_metadata
            }
            
            enriched_chunks.append(enriched_chunk)
            
        return enriched_chunks
