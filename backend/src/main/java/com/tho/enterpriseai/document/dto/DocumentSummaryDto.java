package com.tho.enterpriseai.document.dto;

import java.time.LocalDateTime;
import java.util.UUID;

public record DocumentSummaryDto(
        UUID id,
        String documentCode,
        String title,
        String category,
        LocalDateTime createdAt,
        LocalDateTime updatedAt,
        String createdBy,
        DocumentVersionDto currentVersion
) {
}
