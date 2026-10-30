package com.tho.enterpriseai.document;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface DocumentChunkRepository extends JpaRepository<DocumentChunkEntity, UUID> {

    List<DocumentChunkEntity> findByVersionIdOrderByChunkIndexAsc(UUID versionId);

    Optional<DocumentChunkEntity> findByVersionIdAndChunkId(UUID versionId, String chunkId);

    @Transactional
    void deleteByVersionId(UUID versionId);

    @Transactional
    void deleteByDocumentId(UUID documentId);

    long countByVersionId(UUID versionId);
}
