package com.tho.enterpriseai.document.dto;

import com.fasterxml.jackson.annotation.JsonProperty;

import java.time.LocalDateTime;
import java.util.UUID;

public record DocumentVersionDto(
        UUID id,
        UUID documentId,
        int versionNumber,
        String status,
        int chunkCount,
        int pageCount,
        @JsonProperty("isCurrent") boolean isCurrent,
        String fileHash,
        LocalDateTime createdAt,
        String createdBy,
        String errorMessage
) {
}
