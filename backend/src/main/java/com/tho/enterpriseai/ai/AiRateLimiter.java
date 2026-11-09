package com.tho.enterpriseai.ai;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.dao.DataAccessException;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;

/** Fixed one-minute window per user, shared across backend instances through Redis. */
@Component
public class AiRateLimiter {

    private static final Logger logger = LoggerFactory.getLogger(AiRateLimiter.class);

    private final StringRedisTemplate redis;
    private final int limitPerMinute;

    public AiRateLimiter(
            StringRedisTemplate redis,
            @Value("${app.ai-rate-limit-per-minute:30}") int limitPerMinute
    ) {
        this.redis = redis;
        this.limitPerMinute = limitPerMinute;
    }

    public boolean allow(String userEmail) {
        String key = "ai:rate:" + userEmail + ":" + (System.currentTimeMillis() / 60_000);
        try {
            Long count = redis.opsForValue().increment(key);
            if (count != null && count == 1L) {
                redis.expire(key, Duration.ofMinutes(2));
            }
            return count == null || count <= limitPerMinute;
        } catch (DataAccessException exception) {
            // A cache outage must not take the assistant down.
            logger.warn("Rate limiter unavailable, allowing request: {}", exception.getMessage());
            return true;
        }
    }
}
