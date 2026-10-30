package com.tho.enterpriseai.document.dto;

public record IngestionStatusDto(
        String status,
        int step,
        int chunkCount,
        String message
) {
}
