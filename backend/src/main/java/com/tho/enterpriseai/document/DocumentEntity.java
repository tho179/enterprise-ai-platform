package com.tho.enterpriseai.document;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;
import java.util.UUID;

@Entity
@Table(name = "documents", uniqueConstraints = {
        @UniqueConstraint(name = "uk_documents_code", columnNames = "document_code")
})
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class DocumentEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "document_code", nullable = false, length = 64)
    private String documentCode;

    @Column(nullable = false)
    private String title;

    @Column(nullable = false, length = 64)
    private String category;

    /** Comma-separated roles allowed to read this document; "*" means everyone. */
    @Builder.Default
    @Column(name = "allowed_roles", nullable = false)
    private String allowedRoles = "*";

    public java.util.List<String> allowedRoleList() {
        return java.util.Arrays.stream(allowedRoles.split(","))
                .map(String::trim)
                .filter(role -> !role.isEmpty())
                .toList();
    }

    @Column(name = "created_by", nullable = false)
    private String createdBy;

    @Column(name = "created_at", nullable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;
}
