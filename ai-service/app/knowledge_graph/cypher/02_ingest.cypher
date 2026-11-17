// =====================================================================
// 02_ingest.cypher - Nạp một tài liệu (PDF, link hoặc upload) vào một KB
//
// Tham số: $kb_id, $kb_name, $doc (map thuộc tính Document),
//          $chunks (list map; mỗi chunk có entities, references, applies_to)
// MERGE trên ID theo nội dung nên nạp lại cùng tài liệu không sinh node mới.
// =====================================================================

// :name UPSERT_DOCUMENT
MERGE (kb:KnowledgeBase {kb_id: $kb_id})
  ON CREATE SET kb.name = $kb_name, kb.created_at = datetime()
SET kb.updated_at = datetime()
WITH kb
MERGE (d:Document {doc_id: $doc.doc_id})
  ON CREATE SET d.ingested_at = datetime()
SET d += $doc
MERGE (kb)-[:HAS_DOCUMENT]->(d)
WITH d
UNWIND $chunks AS c
MERGE (ch:Chunk {chunk_id: c.chunk_id})
SET ch.text = c.text,
    ch.chunk_index = c.chunk_index,
    ch.page_start = c.page_start,
    ch.page_end = c.page_end,
    ch.section_path = c.section_path,
    ch.content_hash = c.content_hash,
    ch.version_id = c.version_id
MERGE (d)-[:HAS_CHUNK]->(ch)
WITH DISTINCT d
RETURN d.doc_id AS doc_id, size($chunks) AS chunks;

// Một KB nguồn đã được gộp (KB1 -[:MERGED_INTO]-> KB) thì tài liệu mới nạp
// vào nó cũng phải xuất hiện ngay trong KB đích, không cần chạy gộp lại.
// :name PROPAGATE_TO_MERGED
MATCH (:KnowledgeBase {kb_id: $kb_id})-[:MERGED_INTO]->(target:KnowledgeBase)
MATCH (d:Document {doc_id: $doc_id})
MERGE (target)-[:HAS_DOCUMENT]->(d)
RETURN count(target) AS targets;

// MENTIONS mang độ tin cậy của phép trích xuất (regex điều khoản 0.95,
// alias đầy đủ 0.9, alias tiếng Anh 0.85, viết tắt 0.75, khớp bỏ dấu 0.6).
// :name UPSERT_ENTITIES
UNWIND $chunks AS c
MATCH (ch:Chunk {chunk_id: c.chunk_id})
UNWIND c.entities AS e
MERGE (en:Entity {entity_id: e.entity_id})
  ON CREATE SET en.name = e.name, en.type = e.type
MERGE (ch)-[m:MENTIONS]->(en)
SET m.confidence = coalesce(e.confidence, 1.0),
    m.method = coalesce(e.method, 'unknown')
WITH DISTINCT ch
MATCH (ch)-[:MENTIONS]->(en)
WITH ch, collect(DISTINCT en) AS entities
UNWIND entities AS a
UNWIND entities AS b
WITH a, b
WHERE a.entity_id < b.entity_id
  AND NOT a.type IN ['dieu_khoan', 'moc_thoi_gian']
  AND NOT b.type IN ['dieu_khoan', 'moc_thoi_gian']
MERGE (a)-[r:RELATES_TO]-(b)
  ON CREATE SET r.kind = 'co_mentions', r.weight = 1;

// :name UPSERT_REFERENCES
UNWIND $chunks AS c
UNWIND c.references AS ref
MATCH (source:Chunk {chunk_id: c.chunk_id})
MATCH (target:Chunk {chunk_id: ref.target})
MERGE (source)-[r:REFERENCES]->(target)
SET r.article = ref.article;

// :name UPSERT_APPLIES_TO
UNWIND $chunks AS c
UNWIND c.applies_to AS entity_id
MATCH (chunk:Chunk {chunk_id: c.chunk_id})
MATCH (entity:Entity {entity_id: entity_id})
MERGE (chunk)-[:APPLIES_TO]->(entity);
