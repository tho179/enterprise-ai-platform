package com.tho.enterpriseai.document;

import com.tho.enterpriseai.document.dto.*;
import com.tho.enterpriseai.security.CurrentUser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDateTime;
import java.util.HexFormat;
import java.util.List;
import java.util.Locale;
import java.util.Optional;
import java.util.UUID;
import java.util.regex.Pattern;

@Service
public class DocumentService {

    private static final Logger logger = LoggerFactory.getLogger(DocumentService.class);
    private static final long MAX_FILE_BYTES = 25L * 1024 * 1024;
    private static final Pattern DOCUMENT_CODE = Pattern.compile("^[A-Za-z0-9-]{1,32}$");
    private static final List<String> KNOWN_ROLES = List.of("EMPLOYEE", "MANAGER", "IT_SUPPORT", "ADMIN");

    private final DocumentRepository documentRepository;
    private final DocumentVersionRepository versionRepository;
    private final DocumentChunkRepository chunkRepository;
    private final IngestionTaskRepository taskRepository;
    private final IngestionService ingestionService;
    private final AiIngestClient aiIngestClient;
    private final CurrentUser currentUser;
    private final PdfProcessor pdfProcessor;
    private final Path uploadDir;

    public DocumentService(
            DocumentRepository documentRepository,
            DocumentVersionRepository versionRepository,
            DocumentChunkRepository chunkRepository,
            IngestionTaskRepository taskRepository,
            IngestionService ingestionService,
            AiIngestClient aiIngestClient,
            CurrentUser currentUser,
            PdfProcessor pdfProcessor,
            @Value("${app.upload-dir}") String uploadDir
    ) {
        this.documentRepository = documentRepository;
        this.versionRepository = versionRepository;
        this.chunkRepository = chunkRepository;
        this.taskRepository = taskRepository;
        this.ingestionService = ingestionService;
        this.aiIngestClient = aiIngestClient;
        this.currentUser = currentUser;
        this.pdfProcessor = pdfProcessor;
        this.uploadDir = Paths.get(uploadDir).toAbsolutePath().normalize();
    }

    public UploadTicketDto upload(
            String documentCode,
            String title,
            String category,
            String allowedRoles,
            MultipartFile file
    ) {
        String code = normalizeCode(documentCode);
        String access = normalizeRoles(allowedRoles);
        String cleanTitle = normalizeText(title, "Tiêu đề tài liệu", 200);
        String cleanCategory = normalizeText(category, "Danh mục", 64);

        if (documentRepository.existsByDocumentCodeIgnoreCase(code)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "Mã tài liệu đã tồn tại.");
        }

        StoredFile stored = store(file);
        try {
            LocalDateTime now = LocalDateTime.now();
            DocumentEntity document = documentRepository.save(DocumentEntity.builder()
                    .documentCode(code)
                    .title(cleanTitle)
                    .category(cleanCategory)
                    .allowedRoles(access)
                    .createdBy(currentUser.fullName())
                    .createdAt(now)
                    .updatedAt(now)
                    .build());

            DocumentVersionEntity version = versionRepository.save(DocumentVersionEntity.builder()
                    .documentId(document.getId())
                    .versionNumber(1)
                    .status("PROCESSING")
                    .chunkCount(0)
                    .pageCount(0)
                    .current(true)
                    .fileHash(stored.hash())
                    .fileName(stored.fileName())
                    .storagePath(stored.path().toString())
                    .createdBy(currentUser.fullName())
                    .createdAt(now)
                    .build());

            IngestionTaskEntity task = createTask(document.getId(), version.getId());
            ingestionService.process(task.getId(), false);
            return new UploadTicketDto(task.getId(), version.getId(), document.getId());
        } catch (RuntimeException exception) {
            deleteQuietly(stored.path());
            throw exception;
        }
    }

    public UploadTicketDto uploadVersion(UUID documentId, MultipartFile file) {
        DocumentEntity document = findDocument(documentId);
        List<DocumentVersionEntity> versions = versionRepository.findByDocumentId(documentId);
        boolean processing = versions.stream().anyMatch(item -> "PROCESSING".equals(item.getStatus()));
        if (processing) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT, "Vui lòng đợi phiên bản trước nạp xong.");
        }

        StoredFile stored = store(file);
        try {
            int nextVersion = versions.stream()
                    .mapToInt(DocumentVersionEntity::getVersionNumber)
                    .max()
                    .orElse(0) + 1;
            LocalDateTime now = LocalDateTime.now();
            DocumentVersionEntity version = versionRepository.save(DocumentVersionEntity.builder()
                    .documentId(document.getId())
                    .versionNumber(nextVersion)
                    .status("PROCESSING")
                    .chunkCount(0)
                    .pageCount(0)
                    .current(false)
                    .fileHash(stored.hash())
                    .fileName(stored.fileName())
                    .storagePath(stored.path().toString())
                    .createdBy(currentUser.fullName())
                    .createdAt(now)
                    .build());
            document.setUpdatedAt(now);
            documentRepository.save(document);

            IngestionTaskEntity task = createTask(document.getId(), version.getId());
            ingestionService.process(task.getId(), false);
            return new UploadTicketDto(task.getId(), version.getId(), document.getId());
        } catch (RuntimeException exception) {
            deleteQuietly(stored.path());
            throw exception;
        }
    }

    public UploadTicketDto retry(UUID versionId) {
        DocumentVersionEntity version = versionRepository.findById(versionId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Không tìm thấy phiên bản."));
        if (!"FAILED".equals(version.getStatus())) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT, "Chỉ có thể nạp lại phiên bản đang lỗi.");
        }
        Path file = Path.of(version.getStoragePath());
        if (!Files.exists(file)) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST, "Tệp gốc không còn trên máy chủ, vui lòng tải phiên bản mới.");
        }

        chunkRepository.deleteByVersionId(version.getId());
        version.setStatus("PROCESSING");
        version.setChunkCount(0);
        version.setErrorMessage(null);
        versionRepository.save(version);

        IngestionTaskEntity task = createTask(version.getDocumentId(), version.getId());
        ingestionService.process(task.getId(), false);
        return new UploadTicketDto(task.getId(), version.getId(), version.getDocumentId());
    }

    /** Re-chunk and re-embed the current version from its stored PDF. */
    public UploadTicketDto reindex(UUID versionId) {
        DocumentVersionEntity version = versionRepository.findById(versionId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Không tìm thấy phiên bản."));
        if (!"INGESTED".equals(version.getStatus()) || !version.isCurrent()) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT, "Chỉ nạp lại được phiên bản hiện hành đã nạp xong.");
        }
        if (!Files.exists(Path.of(version.getStoragePath()))) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST, "Tệp gốc không còn trên máy chủ, vui lòng tải phiên bản mới.");
        }

        version.setStatus("PROCESSING");
        version.setErrorMessage(null);
        versionRepository.save(version);

        IngestionTaskEntity task = createTask(version.getDocumentId(), version.getId());
        ingestionService.process(task.getId(), true);
        return new UploadTicketDto(task.getId(), version.getId(), version.getDocumentId());
    }

    public DocumentListDto list(String q, String category, String status) {
        String keyword = (q == null || q.isBlank()) ? null : q.trim();
        String cat = (category == null || category.isBlank()) ? null : category.trim();
        String stat = (status == null || status.isBlank()) ? null : status.trim();

        List<DocumentSummaryDto> items = documentRepository.findByFilters(keyword, cat, stat)
                .stream()
                .filter(this::canRead)
                .map(document -> {
                    DocumentVersionEntity current = currentVersion(document.getId());
                    return current != null ? summary(document, current) : null;
                })
                .filter(dto -> dto != null)
                .toList();

        return new DocumentListDto(items, items.size());
    }

    public DocumentDetailDto get(UUID id) {
        DocumentEntity document = findDocument(id);
        List<DocumentVersionDto> versions = versionRepository
                .findByDocumentIdOrderByVersionNumberDesc(id)
                .stream()
                .map(this::toVersionDto)
                .toList();
        DocumentVersionEntity current = currentVersion(id);
        if (current == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Tài liệu chưa có phiên bản.");
        }
        return new DocumentDetailDto(
                document.getId(),
                document.getDocumentCode(),
                document.getTitle(),
                document.getCategory(),
                document.getCreatedAt(),
                document.getUpdatedAt(),
                document.getCreatedBy(),
                toVersionDto(current),
                versions
        );
    }

    public record StoredPdf(DocumentVersionEntity version, Path file) {
    }

    public List<DocumentVersionDto> versions(UUID id) {
        findDocument(id);
        return versionRepository.findByDocumentIdOrderByVersionNumberDesc(id)
                .stream()
                .map(this::toVersionDto)
                .toList();
    }

    public List<DocumentChunkDto> chunks(UUID id, String q) {
        findDocument(id);
        DocumentVersionEntity current = currentVersion(id);
        if (current == null) {
            return List.of();
        }
        String query = q == null ? "" : q.trim().toLowerCase(Locale.ROOT);
        return chunkRepository.findByVersionIdOrderByChunkIndexAsc(current.getId())
                .stream()
                .filter(chunk -> query.isEmpty()
                        || chunk.getContent().toLowerCase(Locale.ROOT).contains(query)
                        || chunk.getSectionPath().toLowerCase(Locale.ROOT).contains(query))
                .map(this::toChunkDto)
                .toList();
    }

    public DocumentVersionDto setCurrent(UUID versionId) {
        DocumentVersionEntity target = versionRepository.findById(versionId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Không tìm thấy phiên bản."));
        if (!"INGESTED".equals(target.getStatus())) {
            throw new ResponseStatusException(
                    HttpStatus.CONFLICT, "Chỉ đặt phiên bản đã nạp làm hiện hành.");
        }
        DocumentEntity document = findDocument(target.getDocumentId());
        for (DocumentVersionEntity item : versionRepository.findByDocumentId(document.getId())) {
            boolean current = item.getId().equals(target.getId());
            if (item.isCurrent() != current) {
                item.setCurrent(current);
                versionRepository.save(item);
            }
        }
        document.setUpdatedAt(LocalDateTime.now());
        documentRepository.save(document);
        return toVersionDto(target);
    }

    @Transactional
    public int delete(List<UUID> ids) {
        if (ids == null || ids.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Vui lòng chọn tài liệu cần xóa.");
        }
        List<DocumentEntity> documents = documentRepository.findAllById(ids);
        if (documents.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Không tìm thấy tài liệu cần xóa.");
        }

        for (DocumentEntity document : documents) {
            boolean processing = versionRepository.findByDocumentId(document.getId()).stream()
                    .anyMatch(version -> "PROCESSING".equals(version.getStatus()));
            if (processing || taskRepository.existsByDocumentIdAndStatus(document.getId(), "PROCESSING")) {
                throw new ResponseStatusException(
                        HttpStatus.CONFLICT,
                        "Không thể xóa \"" + document.getTitle() + "\" khi đang nạp. Vui lòng đợi pipeline hoàn tất.");
            }
        }

        for (DocumentEntity document : documents) {
            try {
                aiIngestClient.deleteDocumentVectors(document.getId().toString());
            } catch (RuntimeException exception) {
                logger.warn("Cannot delete vectors for document {}", document.getId(), exception);
                throw new ResponseStatusException(
                        HttpStatus.BAD_GATEWAY,
                        "Không xóa được vector của tài liệu. Kiểm tra dịch vụ AI rồi thử lại.");
            }
        }

        for (DocumentEntity document : documents) {
            for (DocumentVersionEntity version : versionRepository.findByDocumentId(document.getId())) {
                deleteQuietly(Path.of(version.getStoragePath()));
            }
            taskRepository.deleteByDocumentId(document.getId());
            chunkRepository.deleteByDocumentId(document.getId());
            versionRepository.deleteByDocumentId(document.getId());
            documentRepository.delete(document);
        }
        return documents.size();
    }

    public IngestionStatusDto status(String taskId) {
        IngestionTaskEntity task = taskRepository.findById(taskId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Không tìm thấy tác vụ nạp."));
        return new IngestionStatusDto(
                task.getStatus(),
                task.getStep(),
                task.getChunkCount(),
                task.getMessage()
        );
    }

    /**
     * Tệp PDF gốc của phiên bản hiện hành để viewer hiển thị.
     */
    public DocumentVersionEntity currentDocumentVersion(UUID documentId) {
        findDocument(documentId);
        DocumentVersionEntity version = versionRepository
                .findByDocumentIdAndCurrentTrue(documentId)
                .orElseGet(() -> versionRepository
                        .findFirstByDocumentIdOrderByVersionNumberDesc(documentId)
                        .orElseThrow(() -> new ResponseStatusException(
                                HttpStatus.NOT_FOUND, "Tài liệu chưa có phiên bản.")));
        return version;
    }

    public StoredPdf openCurrentPdf(UUID documentId) {
        DocumentVersionEntity version = currentDocumentVersion(documentId);
        Path file = Path.of(version.getStoragePath());
        if (!Files.exists(file)) {
            throw new ResponseStatusException(
                    HttpStatus.NOT_FOUND, "Tệp gốc không còn trên máy chủ.");
        }
        return new StoredPdf(version, file);
    }

    private record ChunkSelection(DocumentVersionEntity version, DocumentChunkEntity chunk) {
    }

    /**
     * Chunk của phiên bản hiện hành, hoặc phiên bản cũ mà lịch sử chat còn
     * trích dẫn — để mở lại PDF cũ vẫn đúng tệp và đúng vùng tô vàng.
     */
    private ChunkSelection chunkForRendering(UUID documentId, String chunkId) {
        DocumentVersionEntity current = currentDocumentVersion(documentId);
        Optional<DocumentChunkEntity> currentChunk = chunkRepository
                .findByVersionIdAndChunkId(current.getId(), chunkId);
        if (currentChunk.isPresent()) {
            return new ChunkSelection(current, currentChunk.get());
        }

        DocumentChunkEntity historical = chunkRepository
                .findByDocumentIdAndChunkId(documentId, chunkId)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Không tìm thấy đoạn trích."));
        DocumentVersionEntity version = versionRepository.findById(historical.getVersionId())
                .filter(candidate -> candidate.getDocumentId().equals(documentId))
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Không tìm thấy phiên bản của đoạn trích."));
        return new ChunkSelection(version, historical);
    }

    private Path existingFile(DocumentVersionEntity version) {
        Path file = Path.of(version.getStoragePath());
        if (!Files.exists(file)) {
            throw new ResponseStatusException(
                    HttpStatus.NOT_FOUND, "Tệp gốc không còn trên máy chủ.");
        }
        return file;
    }

    /**
     * Ảnh trang PDF của chunk kèm tô vàng các dòng dẫn chứng (highlightJson).
     * Chunk của các phiên bản cũ vẫn preview được để đối chiếu lịch sử.
     */
    public byte[] renderChunkPreview(UUID documentId, String chunkId) {
        ChunkSelection selection = chunkForRendering(documentId, chunkId);
        List<PdfProcessor.Rect> rects = parseHighlight(selection.chunk().getHighlightJson());
        return pdfProcessor.renderPageWithHighlight(
                existingFile(selection.version()), selection.chunk().getPageStart(), rects, 2.0f);
    }

    /**
     * PDF gốc đã tô vàng dẫn chứng của chunk — dùng cho trình xem PDF thật
     * trong modal trích dẫn, kể cả trích dẫn thuộc phiên bản cũ.
     */
    public byte[] renderChunkPdf(UUID documentId, String chunkId) {
        ChunkSelection selection = chunkForRendering(documentId, chunkId);
        List<PdfProcessor.Rect> rects = parseHighlight(selection.chunk().getHighlightJson());
        return pdfProcessor.renderPdfWithHighlight(
                existingFile(selection.version()), selection.chunk().getPageStart(), rects);
    }

    private List<PdfProcessor.Rect> parseHighlight(String highlightJson) {
        if (highlightJson == null || highlightJson.isBlank()) {
            return List.of();
        }
        java.util.List<PdfProcessor.Rect> rects = new java.util.ArrayList<>();
        // JSON chỉ gồm số, dấu ngoặc và các khóa cố định -> parse gọn bằng regex.
        java.util.regex.Matcher matcher = java.util.regex.Pattern
                .compile("\"x\":(-?[0-9.]+),\"y\":(-?[0-9.]+),\"w\":([0-9.]+),\"h\":([0-9.]+)")
                .matcher(highlightJson);
        while (matcher.find()) {
            rects.add(new PdfProcessor.Rect(
                    Double.parseDouble(matcher.group(1)),
                    Double.parseDouble(matcher.group(2)),
                    Double.parseDouble(matcher.group(3)),
                    Double.parseDouble(matcher.group(4)),
                    ""));
        }
        return rects;
    }

    private IngestionTaskEntity createTask(UUID documentId, UUID versionId) {
        return taskRepository.save(IngestionTaskEntity.builder()
                .id(ingestionService.newTaskId())
                .documentId(documentId)
                .versionId(versionId)
                .status("PROCESSING")
                .step(1)
                .chunkCount(0)
                .message("Đã nhận tệp, chờ xử lý.")
                .updatedAt(LocalDateTime.now())
                .build());
    }

    private DocumentEntity findDocument(UUID id) {
        // A document the user may not read looks the same as a missing one.
        return documentRepository.findById(id)
                .filter(this::canRead)
                .orElseThrow(() -> new ResponseStatusException(
                        HttpStatus.NOT_FOUND, "Không tìm thấy tài liệu."));
    }

    private boolean canRead(DocumentEntity document) {
        String role = currentUser.role();
        List<String> allowed = document.allowedRoleList();
        return "ADMIN".equals(role) || allowed.contains("*") || allowed.contains(role);
    }

    private String normalizeRoles(String value) {
        if (value == null || value.isBlank() || value.trim().equals("*")) {
            return "*";
        }
        List<String> roles = java.util.Arrays.stream(value.split(","))
                .map(role -> role.trim().toUpperCase(Locale.ROOT))
                .filter(role -> !role.isEmpty())
                .distinct()
                .toList();
        if (roles.isEmpty() || !KNOWN_ROLES.containsAll(roles)) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Vai trò được phép xem không hợp lệ.");
        }
        return String.join(",", roles);
    }

    private DocumentVersionEntity currentVersion(UUID documentId) {
        return versionRepository.findByDocumentIdAndCurrentTrue(documentId)
                .orElseGet(() -> versionRepository
                        .findFirstByDocumentIdOrderByVersionNumberDesc(documentId)
                        .orElse(null));
    }

    private DocumentSummaryDto summary(DocumentEntity document, DocumentVersionEntity current) {
        return new DocumentSummaryDto(
                document.getId(),
                document.getDocumentCode(),
                document.getTitle(),
                document.getCategory(),
                document.getCreatedAt(),
                document.getUpdatedAt(),
                document.getCreatedBy(),
                toVersionDto(current)
        );
    }

    private DocumentVersionDto toVersionDto(DocumentVersionEntity version) {
        return new DocumentVersionDto(
                version.getId(),
                version.getDocumentId(),
                version.getVersionNumber(),
                version.getStatus(),
                version.getChunkCount(),
                version.getPageCount(),
                version.isCurrent(),
                version.getFileHash(),
                version.getCreatedAt(),
                version.getCreatedBy(),
                version.getErrorMessage()
        );
    }

    private DocumentChunkDto toChunkDto(DocumentChunkEntity chunk) {
        return new DocumentChunkDto(
                chunk.getId(),
                chunk.getChunkId(),
                chunk.getDocumentId(),
                chunk.getVectorId(),
                chunk.getPageStart(),
                chunk.getPageEnd(),
                chunk.getHeadingLevel(),
                chunk.getSectionPath(),
                chunk.getContent(),
                chunk.getHighlightJson()
        );
    }

    private String normalizeCode(String value) {
        String code = value == null ? "" : value.trim().toUpperCase(Locale.ROOT);
        if (!DOCUMENT_CODE.matcher(code).matches()) {
            throw new ResponseStatusException(
                    HttpStatus.BAD_REQUEST, "Mã tài liệu chỉ gồm chữ, số và dấu gạch ngang (tối đa 32 ký tự).");
        }
        return code;
    }

    private String normalizeText(String value, String label, int maxLength) {
        String text = value == null ? "" : value.trim();
        if (text.isBlank()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Vui lòng nhập " + label.toLowerCase() + ".");
        }
        if (text.length() > maxLength) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, label + " quá dài.");
        }
        return text;
    }

    private StoredFile store(MultipartFile file) {
        if (file == null || file.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Vui lòng chọn tệp PDF.");
        }
        if (file.getSize() > MAX_FILE_BYTES) {
            throw new ResponseStatusException(HttpStatus.PAYLOAD_TOO_LARGE, "Tệp vượt quá 25 MB.");
        }
        String original = file.getOriginalFilename() == null ? "tailieu.pdf" : file.getOriginalFilename();
        String fileName = Paths.get(original).getFileName().toString();
        if (!fileName.toLowerCase(Locale.ROOT).endsWith(".pdf")) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Chỉ hỗ trợ tệp PDF.");
        }
        if (fileName.length() > 255) {
            fileName = fileName.substring(fileName.length() - 255);
        }

        Path target = uploadDir.resolve(UUID.randomUUID() + ".pdf");
        try {
            Files.createDirectories(uploadDir);
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (InputStream input = file.getInputStream();
                 OutputStream output = Files.newOutputStream(target)) {
                byte[] header = input.readNBytes(5);
                if (header.length < 5
                        || header[0] != '%'
                        || header[1] != 'P'
                        || header[2] != 'D'
                        || header[3] != 'F'
                        || header[4] != '-') {
                    throw new ResponseStatusException(
                            HttpStatus.BAD_REQUEST, "Tệp tải lên không phải PDF hợp lệ.");
                }
                output.write(header);
                digest.update(header);
                byte[] buffer = new byte[8192];
                int read;
                while ((read = input.read(buffer)) != -1) {
                    output.write(buffer, 0, read);
                    digest.update(buffer, 0, read);
                }
            }
            return new StoredFile(target, HexFormat.of().formatHex(digest.digest()), fileName);
        } catch (ResponseStatusException exception) {
            deleteQuietly(target);
            throw exception;
        } catch (IOException | NoSuchAlgorithmException exception) {
            deleteQuietly(target);
            throw new ResponseStatusException(
                    HttpStatus.INTERNAL_SERVER_ERROR, "Không lưu được tệp tải lên.");
        }
    }

    private void deleteQuietly(Path path) {
        try {
            Files.deleteIfExists(path);
        } catch (IOException ignored) {
            // The file is orphaned but the API error is still returned to the client.
        }
    }

    private record StoredFile(Path path, String hash, String fileName) {
    }
}
