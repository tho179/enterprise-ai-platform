package com.tho.enterpriseai.document;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.FileSystemResource;
import org.springframework.http.HttpEntity;
import org.springframework.http.MediaType;
import org.springframework.http.client.MultipartBodyBuilder;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;

import java.nio.file.Path;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
public class AiParseClient {

    private static final Logger logger = LoggerFactory.getLogger(AiParseClient.class);
    private static final Pattern ERROR_MESSAGE = Pattern.compile("\"message\"\\s*:\\s*\"((?:\\\\.|[^\"\\\\])*)\"");

    private final RestClient client;

    public AiParseClient(
            @Value("${app.ai-service-url}") String baseUrl,
            @Value("${app.ai-parse-timeout-ms:1800000}") int readTimeoutMs
    ) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(10_000);
        factory.setReadTimeout(readTimeoutMs);
        this.client = RestClient.builder()
                .baseUrl(baseUrl)
                .requestFactory(factory)
                .build();
    }

    public ParseResponse parse(Path file) {
        MultipartBodyBuilder builder = new MultipartBodyBuilder();
        builder.part("file", new FileSystemResource(file))
                .filename(file.getFileName().toString());
        MultiValueMap<String, HttpEntity<?>> body = builder.build();

        try {
            ParseResponse response = client.post()
                    .uri("/api/v1/extract")
                    .contentType(MediaType.MULTIPART_FORM_DATA)
                    .body(body)
                    .retrieve()
                    .body(ParseResponse.class);
            if (response == null || response.pages() == null || response.pages().isEmpty()) {
                throw new IllegalStateException("AI service không trả về nội dung PDF.");
            }
            logger.info(
                    "AI extracted {} pages ({} OCR) for {}",
                    response.pageCount(),
                    response.ocrPages(),
                    file.getFileName()
            );
            return response;
        } catch (ResourceAccessException exception) {
            throw new AiUnavailableException(
                    "Không kết nối được AI service để đọc/OCR PDF. Vui lòng thử lại sau.",
                    exception
            );
        } catch (RestClientResponseException exception) {
            throw new IllegalStateException(errorMessage(exception), exception);
        }
    }

    private String errorMessage(RestClientResponseException exception) {
        String raw = exception.getResponseBodyAsString();
        if (raw != null && !raw.isBlank()) {
            Matcher matcher = ERROR_MESSAGE.matcher(raw);
            if (matcher.find()) {
                return matcher.group(1).replace("\\\"", "\"").replace("\\\\", "\\");
            }
        }
        return "AI service trả lỗi HTTP " + exception.getStatusCode().value() + " khi đọc PDF.";
    }

    public record ParseResponse(
            boolean success,
            int pageCount,
            int nativePages,
            int ocrPages,
            List<Page> pages
    ) {
        public record Page(int page, String text, String source, List<Word> words) {
        }

        public record Word(String text, double x, double y, double w, double h) {
        }
    }

    public static class AiUnavailableException extends RuntimeException {
        public AiUnavailableException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
