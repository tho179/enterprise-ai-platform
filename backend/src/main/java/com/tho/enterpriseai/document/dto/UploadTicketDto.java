package com.tho.enterpriseai.document.dto;

import java.util.UUID;

public record UploadTicketDto(String taskId, UUID versionId, UUID documentId) {
}
