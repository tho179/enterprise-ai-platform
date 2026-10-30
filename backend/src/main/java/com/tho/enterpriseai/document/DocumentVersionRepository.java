package com.tho.enterpriseai.document;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface DocumentVersionRepository extends JpaRepository<DocumentVersionEntity, UUID> {

    List<DocumentVersionEntity> findByDocumentIdOrderByVersionNumberDesc(UUID documentId);

    Optional<DocumentVersionEntity> findByDocumentIdAndCurrentTrue(UUID documentId);

    Optional<DocumentVersionEntity> findFirstByDocumentIdOrderByVersionNumberDesc(UUID documentId);

    List<DocumentVersionEntity> findByDocumentId(UUID documentId);

    @Transactional
    void deleteByDocumentId(UUID documentId);
}
