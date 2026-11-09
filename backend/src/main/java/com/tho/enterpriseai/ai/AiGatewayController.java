package com.tho.enterpriseai.ai;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;

/** The only route from the browser to the AI service. */
@RestController
@RequestMapping("/api/ai")
public class AiGatewayController {

    private final AiGatewayService gateway;

    public AiGatewayController(AiGatewayService gateway) {
        this.gateway = gateway;
    }

    @PostMapping("/chat")
    public Map<String, Object> chat(@RequestBody Map<String, Object> request) {
        return gateway.chat(request);
    }

    @PostMapping("/search")
    public Map<String, Object> search(@RequestBody Map<String, Object> request) {
        return gateway.search(request);
    }

    @GetMapping("/health")
    public Map<String, Object> health() {
        return gateway.status();
    }

    @GetMapping("/audit")
    public List<AiAuditLogEntity> audit(@RequestParam(defaultValue = "50") int limit) {
        return gateway.recentAudit(limit);
    }
}
