package com.tho.enterpriseai.document;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

public interface IngestionTaskRepository extends JpaRepository<IngestionTaskEntity, String> {

    boolean existsByDocumentIdAndStatus(UUID documentId, String status);

    @Transactional
    void deleteByDocumentId(UUID documentId);
}
