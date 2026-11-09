package com.tho.enterpriseai.ai;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "ai_audit_logs")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class AiAuditLogEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "user_email", nullable = false)
    private String userEmail;

    @Column(name = "user_role", nullable = false, length = 64)
    private String userRole;

    @Column(nullable = false, length = 32)
    private String action;

    @Column(name = "query_text", nullable = false, length = 2000)
    private String queryText;

    @Column(name = "document_id", length = 64)
    private String documentId;

    @Column(nullable = false, length = 32)
    private String status;

    @Column(name = "model_used", length = 128)
    private String modelUsed;

    @Column(name = "result_count", nullable = false)
    private int resultCount;

    @Column(name = "latency_ms", nullable = false)
    private long latencyMs;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;
}
