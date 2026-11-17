// =====================================================================
// 06_quality.cypher - Đánh giá chất lượng KB (không cần nhãn)
//
// Năm nhóm chỉ số, mỗi khối trả về một bảng; scripts/18_evaluate_kb.py
// chạy toàn bộ và ghi ra data/eval/results/kb_quality.json:
//   Q_SIZE          quy mô: số node, số cạnh theo loại
//   Q_COVERAGE      độ phủ: tỷ lệ chunk/tài liệu có thực thể
//   Q_INTEGRITY     toàn vẹn: node mồ côi, dẫn chiếu sai, chuỗi phiên bản
//   Q_CONSISTENCY   nhất quán: trùng lặp, hợp nhất mờ, mâu thuẫn dữ kiện
//   Q_CONFIDENCE    độ chắc chắn: phân bố độ tin cậy theo phương pháp
//   Q_FRESHNESS     độ mới: lần cập nhật gần nhất, phiên bản bị thay thế
// Độ chính xác trích xuất (precision) cần nhãn thủ công, xem
// data/eval/kb_entity_sample.json.
// =====================================================================

// :name Q_SIZE
CALL {
  MATCH (n) UNWIND labels(n) AS label
  RETURN label AS kind, count(*) AS total, 'node' AS category
  UNION ALL
  MATCH ()-[r]->()
  RETURN type(r) AS kind, count(*) AS total, 'relationship' AS category
}
RETURN category, kind, total
ORDER BY category, total DESC;

// :name Q_COVERAGE
MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)
WITH d, c,
     COUNT { (c)-[:MENTIONS]->(e:Entity) WHERE NOT e.type IN ['dieu_khoan', 'moc_thoi_gian'] } AS semantic,
     COUNT { (c)-[:MENTIONS]->(:Entity) } AS any_entity
WITH d.source_type AS source_type,
     count(c) AS chunks,
     sum(CASE WHEN any_entity > 0 THEN 1 ELSE 0 END) AS with_entity,
     sum(CASE WHEN semantic > 0 THEN 1 ELSE 0 END) AS with_semantic_entity,
     avg(any_entity) AS avg_entities_per_chunk,
     count(DISTINCT d) AS documents
RETURN source_type, documents, chunks,
       round(toFloat(with_entity) / chunks, 4) AS chunk_entity_coverage,
       round(toFloat(with_semantic_entity) / chunks, 4) AS chunk_semantic_coverage,
       round(avg_entities_per_chunk, 2) AS avg_entities_per_chunk
ORDER BY source_type;

// :name Q_INTEGRITY
RETURN
  COUNT { (c:Chunk) WHERE NOT (:Document)-[:HAS_CHUNK]->(c) } AS orphan_chunks,
  COUNT { (d:Document) WHERE NOT (d)-[:HAS_CHUNK]->(:Chunk) } AS empty_documents,
  COUNT { (d:Document) WHERE NOT (:KnowledgeBase)-[:HAS_DOCUMENT]->(d) } AS documents_without_kb,
  COUNT { (e:Entity) WHERE NOT (e)<-[:MENTIONS]-(:Chunk) } AS orphan_entities,
  COUNT { (a:Chunk)-[:REFERENCES]->(b:Chunk)
          WHERE NOT EXISTS { MATCH (d:Document)-[:HAS_CHUNK]->(a) MATCH (d)-[:HAS_CHUNK]->(b) } } AS cross_document_references,
  COUNT { (n:Document)-[:NEW_VERSION_OF]->(o:Document) WHERE o.is_current } AS stale_versions_still_current,
  COUNT { (x:Claim) WHERE NOT (x)<-[:ASSERTS]-(:Chunk) } AS orphan_claims;

// :name Q_CONSISTENCY
RETURN
  COUNT { (d:Document) WHERE d.duplicate_of IS NOT NULL } AS duplicate_documents,
  COUNT { (a:Entity)-[r:SAME_AS]->(b:Entity) } AS same_as_pairs,
  COUNT { (a:Entity)-[r:POSSIBLY_SAME_AS]->(b:Entity) } AS pending_review_pairs,
  COUNT { (x:Claim) } AS claims,
  COUNT { (x:Claim) WHERE x.status = 'accepted' } AS accepted_claims,
  COUNT { (x:Claim) WHERE x.status = 'superseded' } AS superseded_claims,
  COUNT { (x:Claim) WHERE x.status = 'suspect' } AS suspect_claims,
  COUNT { (x:Claim) WHERE x.status = 'unresolved' } AS unresolved_claims,
  COUNT { ()-[r:CONFLICTS_WITH]->() } AS conflict_edges;

// :name Q_CONFIDENCE
MATCH (:Chunk)-[m:MENTIONS]->(e:Entity)
RETURN coalesce(m.method, 'unknown') AS method, count(*) AS mentions,
       round(avg(coalesce(m.confidence, 1.0)), 3) AS avg_confidence,
       count(DISTINCT e) AS entities
ORDER BY mentions DESC;

// :name Q_RELATION_CONFIDENCE
MATCH (a:Entity)-[r:RELATES_TO]->(b:Entity)
RETURN CASE
         WHEN r.confidence IS NULL THEN 'chua_tinh'
         WHEN r.confidence >= 0.5 THEN 'cao (>=0.5)'
         WHEN r.confidence >= 0.2 THEN 'trung binh (0.2-0.5)'
         ELSE 'thap (<0.2)'
       END AS band,
       count(*) AS relationships
ORDER BY band;

// :name Q_FRESHNESS
OPTIONAL MATCH (r:IngestRun)
WITH r ORDER BY r.finished_at DESC
WITH collect(r)[0] AS last
RETURN
  CASE WHEN last IS NULL THEN null ELSE toString(last.finished_at) END AS last_update,
  CASE WHEN last IS NULL THEN null ELSE last.source END AS last_source,
  COUNT { (r:IngestRun) } AS ingest_runs,
  COUNT { (d:Document) WHERE coalesce(d.is_current, true) } AS current_documents,
  COUNT { (d:Document) WHERE d.is_current = false } AS historical_documents,
  COUNT { (d:Document) WHERE d.effective_date IS NULL } AS documents_without_date;
