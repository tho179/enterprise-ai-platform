package com.tho.enterpriseai.document;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Service
public class AiIngestClient {

    private static final Logger logger = LoggerFactory.getLogger(AiIngestClient.class);
    private static final int BATCH_SIZE = 32;

    private final RestClient client;

    public AiIngestClient(
            @Value("${app.ai-service-url}") String baseUrl,
            @Value("${app.ai-internal-token:}") String internalToken,
            @Value("${app.ai-read-timeout-ms:600000}") int readTimeoutMs
    ) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(10_000);
        factory.setReadTimeout(readTimeoutMs);
        this.client = RestClient.builder()
                .baseUrl(baseUrl)
                .requestFactory(factory)
                .defaultHeader("X-Internal-Token", internalToken)
                .build();
    }

    public void deleteDocumentVectors(String documentId) {
        client.delete()
                .uri("/api/v1/ingest/documents/{documentId}", documentId)
                .retrieve()
                .toBodilessEntity();
    }

    public void deleteVersionVectors(UUID documentId, UUID versionId) {
        client.delete()
                .uri("/api/v1/ingest/documents/{documentId}?version_id={v}", documentId, versionId)
                .retrieve()
                .toBodilessEntity();
    }

    public void ingest(
            DocumentEntity document,
            DocumentVersionEntity version,
            List<DocumentChunkEntity> chunks
    ) {
        for (int start = 0; start < chunks.size(); start += BATCH_SIZE) {
            int end = Math.min(start + BATCH_SIZE, chunks.size());
            List<Map<String, Object>> payload = new ArrayList<>(end - start);
            for (DocumentChunkEntity chunk : chunks.subList(start, end)) {
                Map<String, Object> metadata = new LinkedHashMap<>();
                metadata.put("document_id", document.getId().toString());
                metadata.put("document_code", document.getDocumentCode());
                metadata.put("title", document.getTitle());
                metadata.put("document_type", document.getCategory());
                metadata.put("version_id", version.getId().toString());
                metadata.put("version_number", version.getVersionNumber());
                metadata.put("allowed_roles", document.allowedRoleList());
                metadata.put("page_start", chunk.getPageStart());
                metadata.put("page_end", chunk.getPageEnd());
                metadata.put("chunk_index", chunk.getChunkIndex());
                String section = chunk.getSectionPath();
                metadata.put("section_path", section == null || section.isBlank()
                        ? List.of()
                        : List.of(section.split(" > ")).stream()
                                .map(String::trim)
                                .filter(item -> !item.isBlank())
                                .toList());

                Map<String, Object> item = new LinkedHashMap<>();
                item.put("chunk_id", chunk.getChunkId());
                item.put("content", chunk.getContent());
                item.put("metadata", metadata);
                payload.add(item);
            }

            logger.info("Sending chunks {}-{} of {} to AI service", start + 1, end, chunks.size());
            client.post()
                    .uri("/api/v1/ingest")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(Map.of("chunks", payload))
                    .retrieve()
                    .toBodilessEntity();
        }
    }
}
