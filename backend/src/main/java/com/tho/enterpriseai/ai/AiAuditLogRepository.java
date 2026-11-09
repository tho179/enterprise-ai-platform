package com.tho.enterpriseai.ai;

import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface AiAuditLogRepository extends JpaRepository<AiAuditLogEntity, UUID> {

    List<AiAuditLogEntity> findAllByOrderByCreatedAtDesc(Pageable pageable);
}
