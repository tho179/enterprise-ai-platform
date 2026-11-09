package com.tho.enterpriseai.ai;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.util.Map;

/** HTTP calls to the FastAPI service; only the backend holds its token. */
@Service
public class AiGatewayClient {

    private static final ParameterizedTypeReference<Map<String, Object>> JSON =
            new ParameterizedTypeReference<>() {
            };

    private final RestClient client;

    public AiGatewayClient(
            @Value("${app.ai-service-url}") String baseUrl,
            @Value("${app.ai-internal-token:}") String internalToken,
            @Value("${app.ai-chat-timeout-ms:180000}") int readTimeoutMs
    ) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(5_000);
        factory.setReadTimeout(readTimeoutMs);
        this.client = RestClient.builder()
                .baseUrl(baseUrl)
                .requestFactory(factory)
                .defaultHeader("X-Internal-Token", internalToken)
                .build();
    }

    public Map<String, Object> post(String path, Map<String, Object> body) {
        return client.post()
                .uri(path)
                .contentType(MediaType.APPLICATION_JSON)
                .body(body)
                .retrieve()
                .body(JSON);
    }

    public Map<String, Object> get(String path) {
        return client.get().uri(path).retrieve().body(JSON);
    }
}
