package com.tho.enterpriseai.document;

import com.tho.enterpriseai.document.dto.*;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;
import java.util.UUID;

@RestController
@RequestMapping("/api/documents")
public class DocumentController {

    private final DocumentService documentService;

    public DocumentController(DocumentService documentService) {
        this.documentService = documentService;
    }

    /**
     * Tệp PDF gốc (phiên bản hiện hành) để xem trực tiếp.
     */
    @GetMapping("/{id}/file")
    public ResponseEntity<org.springframework.core.io.FileSystemResource> openFile(@PathVariable UUID id) {
        DocumentService.StoredPdf pdf = documentService.openCurrentPdf(id);
        String fileName = pdf.version().getFileName() == null ? "document.pdf" : pdf.version().getFileName();
        return ResponseEntity.ok()
                .header("Content-Disposition", "inline; filename=\"" + fileName + "\"")
                .contentType(MediaType.APPLICATION_PDF)
                .body(new org.springframework.core.io.FileSystemResource(pdf.file()));
    }

    /**
     * Ảnh trang PDF chứa đoạn trích dẫn, đã tô vàng vùng dẫn chứng.
     */
    @GetMapping("/{id}/chunks/{chunkId}/preview")
    public ResponseEntity<byte[]> chunkPreview(@PathVariable UUID id, @PathVariable String chunkId) {
        byte[] image = documentService.renderChunkPreview(id, chunkId);
        return ResponseEntity.ok()
                .contentType(MediaType.IMAGE_PNG)
                .body(image);
    }

    /**
     * Toàn bộ PDF gốc với đoạn dẫn chứng đã tô vàng, để nhúng trình xem PDF thật.
     */
    @GetMapping("/{id}/chunks/{chunkId}/highlighted")
    public ResponseEntity<byte[]> chunkHighlightedPdf(@PathVariable UUID id, @PathVariable String chunkId) {
        byte[] pdf = documentService.renderChunkPdf(id, chunkId);
        return ResponseEntity.ok()
                .header("Content-Disposition", "inline; filename=\"document-highlighted.pdf\"")
                .contentType(MediaType.APPLICATION_PDF)
                .body(pdf);
    }

    @GetMapping
    public ResponseEntity<DocumentListDto> list(
            @RequestParam(required = false) String q,
            @RequestParam(required = false) String category,
            @RequestParam(required = false) String status
    ) {
        return ResponseEntity.ok(documentService.list(q, category, status));
    }

    @GetMapping("/{id}")
    public ResponseEntity<DocumentDetailDto> get(@PathVariable UUID id) {
        return ResponseEntity.ok(documentService.get(id));
    }

    @GetMapping("/{id}/versions")
    public ResponseEntity<List<DocumentVersionDto>> versions(@PathVariable UUID id) {
        return ResponseEntity.ok(documentService.versions(id));
    }

    @GetMapping("/{id}/chunks")
    public ResponseEntity<List<DocumentChunkDto>> chunks(
            @PathVariable UUID id,
            @RequestParam(required = false) String q
    ) {
        return ResponseEntity.ok(documentService.chunks(id, q));
    }

    @PostMapping("/upload")
    public ResponseEntity<UploadTicketDto> upload(
            @RequestParam String documentCode,
            @RequestParam String title,
            @RequestParam String category,
            @RequestParam(required = false) String allowedRoles,
            @RequestParam("file") MultipartFile file
    ) {
        return ResponseEntity.status(HttpStatus.ACCEPTED)
                .body(documentService.upload(documentCode, title, category, allowedRoles, file));
    }

    @PostMapping("/{id}/versions")
    public ResponseEntity<UploadTicketDto> uploadVersion(
            @PathVariable UUID id,
            @RequestParam("file") MultipartFile file
    ) {
        return ResponseEntity.status(HttpStatus.ACCEPTED)
                .body(documentService.uploadVersion(id, file));
    }

    @PostMapping("/versions/{versionId}/retry")
    public ResponseEntity<UploadTicketDto> retry(@PathVariable UUID versionId) {
        return ResponseEntity.status(HttpStatus.ACCEPTED)
                .body(documentService.retry(versionId));
    }

    @PostMapping("/versions/{versionId}/reindex")
    public ResponseEntity<UploadTicketDto> reindex(@PathVariable UUID versionId) {
        return ResponseEntity.status(HttpStatus.ACCEPTED)
                .body(documentService.reindex(versionId));
    }

    @PatchMapping("/versions/{versionId}/current")
    public ResponseEntity<DocumentVersionDto> setCurrent(@PathVariable UUID versionId) {
        return ResponseEntity.ok(documentService.setCurrent(versionId));
    }

    @DeleteMapping
    public ResponseEntity<Map<String, Integer>> delete(@RequestBody List<UUID> ids) {
        return ResponseEntity.ok(Map.of("deleted", documentService.delete(ids)));
    }
}
