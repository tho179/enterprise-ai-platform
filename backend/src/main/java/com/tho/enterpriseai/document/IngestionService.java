package com.tho.enterpriseai.document;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.nio.file.Path;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Service
public class IngestionService {

    private static final Logger logger = LoggerFactory.getLogger(IngestionService.class);

    private final DocumentRepository documentRepository;
    private final DocumentVersionRepository versionRepository;
    private final DocumentChunkRepository chunkRepository;
    private final IngestionTaskRepository taskRepository;
    private final PdfProcessor pdfProcessor;
    private final AiParseClient aiParseClient;
    private final AiIngestClient aiIngestClient;

    public IngestionService(
            DocumentRepository documentRepository,
            DocumentVersionRepository versionRepository,
            DocumentChunkRepository chunkRepository,
            IngestionTaskRepository taskRepository,
            PdfProcessor pdfProcessor,
            AiParseClient aiParseClient,
            AiIngestClient aiIngestClient
    ) {
        this.documentRepository = documentRepository;
        this.versionRepository = versionRepository;
        this.chunkRepository = chunkRepository;
        this.taskRepository = taskRepository;
        this.pdfProcessor = pdfProcessor;
        this.aiParseClient = aiParseClient;
        this.aiIngestClient = aiIngestClient;
    }

    /**
     * @param replaceExisting re-chunk a version that is already ingested. The old
     *                        chunks stay searchable until the new ones are ready.
     */
    @Async("ingestionExecutor")
    public void process(String taskId, boolean replaceExisting) {
        IngestionTaskEntity task = taskRepository.findById(taskId).orElse(null);
        if (task == null) {
            logger.warn("Ingestion task {} no longer exists", taskId);
            return;
        }
        DocumentEntity document = documentRepository.findById(task.getDocumentId()).orElse(null);
        DocumentVersionEntity version = versionRepository.findById(task.getVersionId()).orElse(null);
        if (document == null || version == null) {
            fail(task, null, "Không tìm thấy tài liệu hoặc phiên bản.");
            return;
        }

        try {
            updateTask(task, "PROCESSING", 1, 0, "Đang đọc và OCR tệp PDF.");
            Path file = Path.of(version.getStoragePath());
            int ocrPages = 0;
            int pageCount;
            PdfProcessor.PdfContent fallbackContent = null;
            AiParseClient.ParseResponse parsed = null;
            try {
                parsed = aiParseClient.parse(file);
                ocrPages = parsed.ocrPages();
                pageCount = parsed.pageCount();
            } catch (RuntimeException aiException) {
                logger.warn("AI PDF extraction failed for {}, trying PDFBox: {}",
                        file, aiException.getMessage());
                try {
                    fallbackContent = pdfProcessor.extract(file);
                    pageCount = fallbackContent.pageCount();
                } catch (RuntimeException pdfException) {
                    aiException.addSuppressed(pdfException);
                    throw aiException;
                }
            }

            version.setPageCount(pageCount);
            version.setChunkCount(0);
            version.setErrorMessage(null);
            versionRepository.save(version);
            String ocrNote = ocrPages > 0 ? " (OCR " + ocrPages + " trang)" : "";
            updateTask(task, "PROCESSING", 2, 0,
                    "Đã trích xuất " + pageCount + " trang" + ocrNote + ", đang chia đoạn.");

            List<DocumentChunkEntity> chunks;
            if (parsed != null && parsed.chunks() != null && !parsed.chunks().isEmpty()) {
                chunks = buildAiChunks(document, version, parsed);
            } else {
                chunks = List.of();
            }
            if (chunks.isEmpty()) {
                if (fallbackContent == null) {
                    fallbackContent = pdfProcessor.fromPages(
                            parsed.pageCount(),
                            toPageTexts(parsed)
                    );
                }
                logger.warn("Version {} has no structured chunks; using page-based fallback", version.getId());
                chunks = buildPageChunks(document, version, fallbackContent);
            }
            if (replaceExisting) {
                chunkRepository.deleteByVersionId(version.getId());
                aiIngestClient.deleteVersionVectors(document.getId(), version.getId());
            }
            chunkRepository.saveAll(chunks);
            version.setChunkCount(chunks.size());
            versionRepository.save(version);
            updateTask(task, "PROCESSING", 3, chunks.size(),
                    "Đã tạo " + chunks.size() + " đoạn trích, đang tạo embedding.");

            aiIngestClient.ingest(document, version, chunks);
            updateTask(task, "PROCESSING", 4, chunks.size(), "Đang ghi kho vector.");

            // Lưu INGESTED trước, rồi mới đánh dấu current: luồng @Async không có
            // shared session nên save(version) sau markCurrent sẽ merge lại bản sao
            // stale (is_current=false) và ghi đè mất cờ just-lưu.
            version.setStatus("INGESTED");
            version.setErrorMessage(null);
            versionRepository.save(version);
            markCurrent(document, version);
            dropSupersededVectors(document.getId(), version.getId());
            updateTask(task, "INGESTED", 5, chunks.size(),
                    "Đã tạo " + chunks.size() + " đoạn trích và đưa tài liệu vào kho vector.");
        } catch (Throwable exception) {
            logger.error("PDF ingestion failed for task {}", taskId, exception);
            fail(task, version, friendlyMessage(exception));
        }
    }

    private List<DocumentChunkEntity> buildAiChunks(
            DocumentEntity document,
            DocumentVersionEntity version,
            AiParseClient.ParseResponse parsed
    ) {
        Map<Integer, List<PdfProcessor.Rect>> wordsByPage = new HashMap<>();
        if (parsed.pages() != null) {
            for (AiParseClient.ParseResponse.Page page : parsed.pages()) {
                wordsByPage.put(page.page(), toWords(page.words()));
            }
        }

        List<DocumentChunkEntity> chunks = new ArrayList<>(parsed.chunks().size());
        for (AiParseClient.ParseResponse.Chunk chunk : parsed.chunks()) {
            String content = chunk.content();
            if (content == null || content.isBlank()) {
                continue;
            }
            int pageStart = chunk.pageStart() > 0 ? chunk.pageStart() : 1;
            int pageEnd = chunk.pageEnd() >= pageStart ? chunk.pageEnd() : pageStart;
            String sectionPath = (chunk.sectionPath() == null ? List.<String>of() : chunk.sectionPath())
                    .stream()
                    .filter(item -> item != null && !item.isBlank())
                    .collect(Collectors.joining(" > "));
            if (sectionPath.isBlank()) {
                sectionPath = "Trang " + pageStart;
            }
            String chunkId = "doc-" + document.getId() + "-v" + version.getVersionNumber()
                    + "-c" + chunk.index();
            List<PdfProcessor.Rect> highlight = pdfProcessor.locateInPage(
                    new PdfProcessor.PageText(
                            pageStart,
                            "",
                            wordsByPage.getOrDefault(pageStart, List.of())),
                    content
            );
            chunks.add(DocumentChunkEntity.builder()
                    .documentId(document.getId())
                    .versionId(version.getId())
                    .chunkId(chunkId)
                    .chunkIndex(chunk.index())
                    .vectorId(chunkId)
                    .pageStart(pageStart)
                    .pageEnd(pageEnd)
                    .headingLevel(chunk.headingLevel())
                    .sectionPath(sectionPath)
                    .content(content)
                    .highlightJson(toHighlightJson(highlight))
                    .build());
        }
        return chunks;
    }

    private List<DocumentChunkEntity> buildPageChunks(
            DocumentEntity document,
            DocumentVersionEntity version,
            PdfProcessor.PdfContent content
    ) {
        List<DocumentChunkEntity> chunks = new ArrayList<>(content.chunks().size());
        for (PdfProcessor.ExtractedChunk extracted : content.chunks()) {
            String chunkId = "doc-" + document.getId() + "-v" + version.getVersionNumber()
                    + "-c" + extracted.index();
            chunks.add(DocumentChunkEntity.builder()
                    .documentId(document.getId())
                    .versionId(version.getId())
                    .chunkId(chunkId)
                    .chunkIndex(extracted.index())
                    .vectorId(chunkId)
                    .pageStart(extracted.page())
                    .pageEnd(extracted.page())
                    .headingLevel(0)
                    .sectionPath("Trang " + extracted.page())
                    .content(extracted.content())
                    .highlightJson(toHighlightJson(extracted.highlight()))
                    .build());
        }
        return chunks;
    }

    private void markCurrent(DocumentEntity document, DocumentVersionEntity target) {
        List<DocumentVersionEntity> versions = versionRepository.findByDocumentId(document.getId());
        for (DocumentVersionEntity item : versions) {
            boolean current = item.getId().equals(target.getId());
            if (item.isCurrent() != current) {
                item.setCurrent(current);
                versionRepository.save(item);
            }
        }
        document.setUpdatedAt(LocalDateTime.now());
        documentRepository.save(document);
    }

    /**
     * Sau khi phiên bản mới nạp xong và trở thành current, xóa vector của các
     * phiên bản cũ để tránh trùng lặp/câu trả lời ám chỉ dữ liệu đã bị thay thế.
     */
    private void dropSupersededVectors(UUID documentId, UUID currentVersionId) {
        try {
            List<UUID> superseded = versionRepository.findByDocumentId(documentId).stream()
                    .filter(item -> !item.getId().equals(currentVersionId))
                    .map(DocumentVersionEntity::getId)
                    .collect(Collectors.toList());
            for (UUID versionId : superseded) {
                try {
                    aiIngestClient.deleteVersionVectors(documentId, versionId);
                    logger.info("Removed superseded vectors of version {} (document {})", versionId, documentId);
                } catch (RuntimeException exception) {
                    logger.warn("Cannot remove vectors of version {} (document {})",
                            versionId, documentId, exception);
                }
            }
        } catch (RuntimeException exception) {
            logger.warn("Cannot enumerate superseded versions for document {}", documentId, exception);
        }
    }

    private List<PdfProcessor.PageText> toPageTexts(AiParseClient.ParseResponse parsed) {
        if (parsed.pages() == null) {
            return List.of();
        }
        return parsed.pages().stream()
                .map(page -> new PdfProcessor.PageText(
                        page.page(),
                        page.text(),
                        toWords(page.words())))
                .toList();
    }

    private List<PdfProcessor.Rect> toWords(List<AiParseClient.ParseResponse.Word> words) {
        if (words == null || words.isEmpty()) {
            return List.of();
        }
        return words.stream()
                .filter(word -> word.text() != null && !word.text().isBlank())
                .map(word -> new PdfProcessor.Rect(word.x(), word.y(), word.w(), word.h(), word.text()))
                .collect(Collectors.toList());
    }

    /**
     * Serialize danh sách khung dòng thành JSON dạng
     * [{"x":0.1,"y":0.2,"w":0.3,"h":0.05}] hoặc null nếu không có.
     */
    private String toHighlightJson(List<PdfProcessor.Rect> rects) {
        if (rects == null || rects.isEmpty()) {
            return null;
        }
        StringBuilder json = new StringBuilder("[");
        for (int i = 0; i < rects.size(); i++) {
            PdfProcessor.Rect rect = rects.get(i);
            if (i > 0) {
                json.append(',');
            }
            json.append("{\"x\":").append(writeNumber(rect.x()))
                    .append(",\"y\":").append(writeNumber(rect.y()))
                    .append(",\"w\":").append(writeNumber(rect.w()))
                    .append(",\"h\":").append(writeNumber(rect.h()))
                    .append('}');
        }
        return json.append(']').toString();
    }

    private String writeNumber(double value) {
        return String.format(java.util.Locale.ROOT, "%.5f", value);
    }

    private void fail(IngestionTaskEntity task, DocumentVersionEntity version, String message) {
        if (version != null) {
            version.setStatus("FAILED");
            version.setErrorMessage(message);
            versionRepository.save(version);
        }
        updateTask(task, "FAILED", task.getStep(), task.getChunkCount(), message);
    }

    private void updateTask(
            IngestionTaskEntity task,
            String status,
            int step,
            int chunkCount,
            String message
    ) {
        task.setStatus(status);
        task.setStep(step);
        task.setChunkCount(chunkCount);
        task.setMessage(message);
        task.setUpdatedAt(LocalDateTime.now());
        taskRepository.save(task);
    }

    private String friendlyMessage(Throwable exception) {
        String message = exception.getMessage();
        if (message == null || message.isBlank()) {
            message = exception.getClass().getSimpleName();
        }
        if (message.length() > 1800) {
            message = message.substring(0, 1800);
        }
        return message;
    }

    public String newTaskId() {
        return "task-" + UUID.randomUUID();
    }
}
