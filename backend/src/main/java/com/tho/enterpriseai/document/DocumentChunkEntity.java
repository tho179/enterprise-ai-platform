package com.tho.enterpriseai.document;

import jakarta.persistence.*;
import lombok.*;

import java.util.UUID;

@Entity
@Table(name = "document_chunks", indexes = {
        @Index(name = "idx_chunks_document", columnList = "document_id"),
        @Index(name = "idx_chunks_version", columnList = "version_id")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DocumentChunkEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "document_id", nullable = false)
    private UUID documentId;

    @Column(name = "version_id", nullable = false)
    private UUID versionId;

    @Column(name = "chunk_id", nullable = false, unique = true, length = 128)
    private String chunkId;

    @Column(name = "chunk_index", nullable = false)
    private int chunkIndex;

    @Column(name = "vector_id", nullable = false, length = 128)
    private String vectorId;

    @Column(name = "page_start", nullable = false)
    private int pageStart;

    @Column(name = "page_end", nullable = false)
    private int pageEnd;

    @Column(name = "heading_level", nullable = false)
    private int headingLevel;

    @Column(name = "section_path", nullable = false, length = 512)
    private String sectionPath;

    @Column(nullable = false, columnDefinition = "text")
    private String content;

    /** JSON danh sách khung dòng dẫn chứng theo tỷ lệ 0..1, ví dụ [{"x":0.1,...}] */
    @Column(columnDefinition = "text")
    private String highlightJson;
}
