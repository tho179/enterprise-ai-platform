package com.tho.enterpriseai.ai;

import com.tho.enterpriseai.security.CurrentUser;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.http.HttpStatus;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.server.ResponseStatusException;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AiGatewayServiceTest {

    private final AiGatewayClient client = mock(AiGatewayClient.class);
    private final AiRateLimiter limiter = mock(AiRateLimiter.class);
    private final AiAuditLogRepository audit = mock(AiAuditLogRepository.class);
    private final CurrentUser user = mock(CurrentUser.class);
    private final AiGatewayService service = new AiGatewayService(client, limiter, audit, user);

    @BeforeEach
    void signedInEmployee() {
        when(user.email()).thenReturn("nva@congty.vn");
        when(user.role()).thenReturn("EMPLOYEE");
        when(limiter.allow(anyString())).thenReturn(true);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> forwardedBody() {
        ArgumentCaptor<Map<String, Object>> body = ArgumentCaptor.forClass(Map.class);
        verify(client).post(eq("/api/v1/chat/ask"), body.capture());
        return body.getValue();
    }

    @Test
    void replacesClientSuppliedRolesWithTheTokenRole() {
        when(client.post(anyString(), any())).thenReturn(Map.of("citations", List.of(1), "model_used", "m"));
        Map<String, Object> request = new HashMap<>(Map.of("query", "q", "user_roles", List.of("ADMIN")));

        service.chat(request);

        assertEquals(List.of("EMPLOYEE"), forwardedBody().get("user_roles"));
    }

    @Test
    void adminIsNotFiltered() {
        when(user.role()).thenReturn("ADMIN");
        when(client.post(anyString(), any())).thenReturn(Map.of());

        service.chat(new HashMap<>(Map.of("query", "q", "user_roles", List.of("EMPLOYEE"))));

        assertFalse(forwardedBody().containsKey("user_roles"));
    }

    @Test
    void rateLimitedRequestNeverReachesTheAiService() {
        when(limiter.allow(anyString())).thenReturn(false);

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.chat(new HashMap<>(Map.of("query", "q"))));

        assertEquals(HttpStatus.TOO_MANY_REQUESTS, error.getStatusCode());
        verify(client, never()).post(anyString(), any());
        verify(audit).save(any());
    }

    @Test
    void aiOutageIsReportedAsBadGatewayAndAudited() {
        when(client.post(anyString(), any())).thenThrow(new ResourceAccessException("down"));

        ResponseStatusException error = assertThrows(ResponseStatusException.class,
                () -> service.chat(new HashMap<>(Map.of("query", "q"))));

        assertEquals(HttpStatus.BAD_GATEWAY, error.getStatusCode());
        ArgumentCaptor<AiAuditLogEntity> entry = ArgumentCaptor.forClass(AiAuditLogEntity.class);
        verify(audit).save(entry.capture());
        assertEquals("ERROR", entry.getValue().getStatus());
    }
}
