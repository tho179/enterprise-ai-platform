// =====================================================================
// 04_update.cypher - Cơ chế cập nhật KB
//
//   nguồn mới                 -> insert
//   cùng nguồn, cùng hash      -> skip (không ghi gì)
//   cùng nguồn, hash khác      -> new_version: bản cũ is_current=false,
//                                 bản mới -[:NEW_VERSION_OF]-> bản cũ
//   nguồn biến mất khỏi thư mục -> retire: is_current=false, giữ lịch sử
//   mỗi lần chạy               -> một node IngestRun ghi số liệu
// Truy xuất chỉ đọc tài liệu có is_current = true (xem 05_retrieval).
// =====================================================================

// :name FIND_CURRENT
MATCH (d:Document {source_uri: $source_uri, is_current: true})
RETURN d { .doc_id, .content_hash, .version } AS doc
ORDER BY d.version DESC
LIMIT 1;

// :name SUPERSEDE_DOCUMENT
MATCH (d:Document {source_uri: $source_uri, is_current: true})
SET d.is_current = false, d.superseded_at = datetime(),
    d.superseded_reason = 'content_changed'
RETURN d.doc_id AS old_doc_id
ORDER BY d.version DESC
LIMIT 1;

// :name LINK_VERSION
MATCH (old:Document {doc_id: $old_doc_id})
MATCH (new:Document {doc_id: $new_doc_id})
MERGE (new)-[r:NEW_VERSION_OF]->(old)
SET r.method = 'content_hash', old.superseded_by = new.doc_id;

// Tài liệu từng nạp từ thư mục $prefix nhưng nay không còn trong $present.
// :name RETIRE_MISSING
MATCH (:KnowledgeBase {kb_id: $kb_id})-[:HAS_DOCUMENT]->(d:Document)
WHERE d.source_type = $source_type
  AND coalesce(d.is_current, true)
  AND d.source_uri STARTS WITH $prefix
  AND NOT d.source_uri IN $present
SET d.is_current = false, d.retired_at = datetime(),
    d.superseded_reason = 'source_removed'
RETURN collect(d.doc_id) AS retired;

// :name LOG_RUN
MATCH (kb:KnowledgeBase {kb_id: $kb_id})
CREATE (r:IngestRun {
  run_id: $run_id, kb_id: $kb_id, source: $source,
  started_at: datetime($started_at), finished_at: datetime(),
  inserted: $inserted, skipped: $skipped, new_version: $new_version,
  retired: $retired, failed: $failed
})
MERGE (r)-[:UPDATED]->(kb)
RETURN r.run_id AS run_id;

// :name DELETE_DOCUMENT_CHUNKS
MATCH (d:Document {doc_id: $document_id})-[:HAS_CHUNK]->(c:Chunk)
WHERE $version_id IS NULL OR c.version_id = $version_id
WITH collect(c) AS chunks
WITH chunks, size(chunks) AS total
FOREACH (chunk IN chunks | DETACH DELETE chunk)
RETURN total AS deleted;

// :name DELETE_DOCUMENT_NODE
MATCH (d:Document {doc_id: $document_id})
DETACH DELETE d;

// :name DELETE_EMPTY_DOCUMENT
MATCH (d:Document {doc_id: $document_id})
WHERE NOT (d)-[:HAS_CHUNK]->(:Chunk)
DETACH DELETE d
RETURN count(d) AS deleted;

// :name DELETE_ORPHAN_ENTITIES
MATCH (e:Entity)
WHERE NOT (e)<-[:MENTIONS]-(:Chunk)
DETACH DELETE e
RETURN count(e) AS deleted;

// Claim của chunk đã xoá thì không còn nguồn để trích dẫn.
// :name DELETE_ORPHAN_CLAIMS
MATCH (x:Claim)
WHERE NOT (x)<-[:ASSERTS]-(:Chunk)
DETACH DELETE x
RETURN count(x) AS deleted;
