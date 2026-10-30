package com.tho.enterpriseai.document.dto;

import java.util.List;

public record DocumentListDto(List<DocumentSummaryDto> items, int total) {
}
