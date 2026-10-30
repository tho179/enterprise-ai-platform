package com.tho.enterpriseai.document.dto;

import java.util.UUID;

public record DocumentChunkDto(
        UUID id,
        String chunkId,
        UUID documentId,
        String vectorId,
        int pageStart,
        int pageEnd,
        int headingLevel,
        String sectionPath,
        String content,
        String highlightJson
) {
}
