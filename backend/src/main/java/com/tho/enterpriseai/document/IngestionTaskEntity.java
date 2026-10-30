package com.tho.enterpriseai.document;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import lombok.*;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "ingestion_tasks", indexes = {
        @Index(name = "idx_tasks_document", columnList = "document_id")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class IngestionTaskEntity {

    @Id
    @Column(length = 64)
    private String id;

    @Column(name = "document_id", nullable = false)
    private UUID documentId;

    @Column(name = "version_id", nullable = false)
    private UUID versionId;

    @Column(nullable = false, length = 32)
    private String status;

    @Column(nullable = false)
    private int step;

    @Column(name = "chunk_count", nullable = false)
    private int chunkCount;

    @Column(length = 2000)
    private String message;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
