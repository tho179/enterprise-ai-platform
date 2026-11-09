package com.tho.enterpriseai.ai;

import com.tho.enterpriseai.security.CurrentUser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/** Applies identity, role filter, rate limit and audit to every AI call. */
@Service
public class AiGatewayService {

    private static final Logger logger = LoggerFactory.getLogger(AiGatewayService.class);
    private static final int MAX_AUDIT_QUERY_CHARS = 2000;

    private final AiGatewayClient client;
    private final AiRateLimiter rateLimiter;
    private final AiAuditLogRepository auditRepository;
    private final CurrentUser currentUser;

    public AiGatewayService(
            AiGatewayClient client,
            AiRateLimiter rateLimiter,
            AiAuditLogRepository auditRepository,
            CurrentUser currentUser
    ) {
        this.client = client;
        this.rateLimiter = rateLimiter;
        this.auditRepository = auditRepository;
        this.currentUser = currentUser;
    }

    public Map<String, Object> chat(Map<String, Object> request) {
        return forward("CHAT", "/api/v1/chat/ask", request, "citations");
    }

    public Map<String, Object> search(Map<String, Object> request) {
        return forward("SEARCH", "/api/v1/search", request, "data");
    }

    public Map<String, Object> status() {
        Map<String, Object> result = new HashMap<>();
        try {
            result.putAll(client.get("/api/v1/search/stats"));
            result.put("status", "healthy");
        } catch (RestClientException exception) {
            logger.warn("AI service status check failed: {}", exception.getMessage());
            result.put("status", "down");
        }
        return result;
    }

    public List<AiAuditLogEntity> recentAudit(int limit) {
        return auditRepository.findAllByOrderByCreatedAtDesc(PageRequest.of(0, Math.min(Math.max(limit, 1), 200)));
    }

    private Map<String, Object> forward(
            String action,
            String path,
            Map<String, Object> request,
            String resultField
    ) {
        String email = currentUser.email();
        String role = currentUser.role();
        String query = String.valueOf(request.getOrDefault("query", ""));
        Object documentId = request.get("document_id");
        long started = System.currentTimeMillis();

        if (!rateLimiter.allow(email)) {
            audit(email, role, action, query, documentId, "RATE_LIMITED", null, 0, started);
            throw new ResponseStatusException(
                    HttpStatus.TOO_MANY_REQUESTS, "Bạn gửi quá nhiều yêu cầu, vui lòng thử lại sau một phút.");
        }

        Map<String, Object> body = new HashMap<>(request);
        // The client never chooses its own roles; ADMIN alone sees every document.
        body.remove("user_roles");
        if (!"ADMIN".equals(role)) {
            body.put("user_roles", List.of(role));
        }

        try {
            Map<String, Object> response = client.post(path, body);
            Object results = response == null ? null : response.get(resultField);
            Object model = response == null ? null : response.get("model_used");
            audit(email, role, action, query, documentId, "OK",
                    model == null ? null : model.toString(),
                    results instanceof List<?> list ? list.size() : 0,
                    started);
            return response;
        } catch (RestClientException exception) {
            logger.error("AI gateway {} failed", action, exception);
            audit(email, role, action, query, documentId, "ERROR", null, 0, started);
            throw new ResponseStatusException(
                    HttpStatus.BAD_GATEWAY, "Dịch vụ AI đang gặp sự cố, vui lòng thử lại sau.");
        }
    }

    private void audit(
            String email,
            String role,
            String action,
            String query,
            Object documentId,
            String status,
            String model,
            int resultCount,
            long started
    ) {
        try {
            auditRepository.save(AiAuditLogEntity.builder()
                    .userEmail(email)
                    .userRole(role)
                    .action(action)
                    .queryText(query.length() > MAX_AUDIT_QUERY_CHARS
                            ? query.substring(0, MAX_AUDIT_QUERY_CHARS)
                            : query)
                    .documentId(documentId == null ? null : documentId.toString())
                    .status(status)
                    .modelUsed(model)
                    .resultCount(resultCount)
                    .latencyMs(System.currentTimeMillis() - started)
                    .createdAt(LocalDateTime.now())
                    .build());
        } catch (RuntimeException exception) {
            logger.warn("Could not write AI audit entry: {}", exception.getMessage());
        }
    }
}
