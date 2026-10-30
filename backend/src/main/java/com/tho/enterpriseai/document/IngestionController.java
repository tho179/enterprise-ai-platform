package com.tho.enterpriseai.document;

import com.tho.enterpriseai.document.dto.IngestionStatusDto;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/ai")
public class IngestionController {

    private final DocumentService documentService;

    public IngestionController(DocumentService documentService) {
        this.documentService = documentService;
    }

    @GetMapping("/status/{taskId}")
    public ResponseEntity<IngestionStatusDto> status(@PathVariable String taskId) {
        return ResponseEntity.ok(documentService.status(taskId));
    }
}
