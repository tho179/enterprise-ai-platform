package com.tho.enterpriseai.document;

import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;
import java.util.Optional;
import java.util.UUID;

public interface DocumentRepository extends JpaRepository<DocumentEntity, UUID> {

    boolean existsByDocumentCodeIgnoreCase(String documentCode);

    Optional<DocumentEntity> findByDocumentCodeIgnoreCase(String documentCode);

    /**
     * Filters documents by optional keyword (title or code), category, and current-version status.
     * All filter parameters are optional — passing null or empty string skips that filter.
     */
    @Query("""
            SELECT d FROM DocumentEntity d
            WHERE (:keyword IS NULL OR :keyword = '' OR
                   LOWER(d.title) LIKE LOWER(CONCAT('%', :keyword, '%')) OR
                   LOWER(d.documentCode) LIKE LOWER(CONCAT('%', :keyword, '%')))
              AND (:category IS NULL OR :category = '' OR LOWER(d.category) = LOWER(:category))
              AND (:status IS NULL OR :status = '' OR EXISTS (
                   SELECT v FROM DocumentVersionEntity v
                   WHERE v.documentId = d.id AND v.current = true
                     AND LOWER(v.status) = LOWER(:status)
              ))
            ORDER BY d.updatedAt DESC
            """)
    List<DocumentEntity> findByFilters(
            @Param("keyword") String keyword,
            @Param("category") String category,
            @Param("status") String status
    );
}
