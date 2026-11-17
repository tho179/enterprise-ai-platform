// =====================================================================
// 05_retrieval.cypher - Truy xuất đồ thị cho luồng RAG (GraphRAG)
//
// Mọi truy vấn lọc qua cùng điều kiện:
//   - tài liệu hiện hành (is_current) và không phải bản trùng (duplicate_of)
//   - bộ lọc quyền: source_type, document_id, allowed_roles
//   - MENTIONS có độ tin cậy >= $min_confidence
// Kết quả trả về cùng dạng cột để service.graph_hit_from_row() chuyển thành
// hit giống Qdrant, rồi được trộn với vector hits bằng RRF.
// =====================================================================

// Bước 1: thực thể trong câu hỏi -> chunk nhắc đến thực thể đó, hoặc
// thực thể kề nó một bước. Thực thể đánh số ("Điều 5") không được đi tiếp
// sang hàng xóm vì nó xuất hiện ở mọi tài liệu.
// :name GRAPH_CANDIDATES
MATCH (seed:Entity)
WHERE seed.name IN $names
MATCH (seed)-[:RELATES_TO*0..1]-(e:Entity)<-[m:MENTIONS]-(c:Chunk)<-[:HAS_CHUNK]-(d:Document)
MATCH (kb:KnowledgeBase)-[:HAS_DOCUMENT]->(d)
WHERE kb.kb_id IN $kb_ids
  AND coalesce(m.confidence, 1.0) >= $min_confidence
  AND (seed = e OR NOT seed.type IN ['dieu_khoan', 'moc_thoi_gian'])
  AND coalesce(d.is_current, true) AND d.duplicate_of IS NULL
  AND ($source_type IS NULL OR d.source_type = $source_type)
  AND ($document_id IS NULL OR d.doc_id = $document_id)
  AND ($roles IS NULL OR any(role IN coalesce(d.allowed_roles, []) WHERE role IN $roles OR role = '*'))
WITH c, d,
     count(DISTINCT CASE WHEN seed = e THEN seed END) AS matched,
     count(DISTINCT CASE WHEN seed <> e THEN e END) AS related,
     count { (c)-[:APPLIES_TO]->(x:Entity) WHERE x.name IN $names } AS heading_matches
WITH c, d, matched + heading_matches AS matched, related
WHERE matched > 0 OR related > 0
RETURN c.chunk_id AS chunk_id, c.text AS content, d.doc_id AS document_id,
       d.title AS title, d.document_type AS document_type,
       d.source_type AS source_type, c.page_start AS page_start,
       c.page_end AS page_end, c.section_path AS section_path,
       matched, related, 'entity' AS via
ORDER BY matched DESC, related ASC, c.chunk_index
LIMIT $limit;

// Bước 2a: điều khoản được dẫn chiếu bởi (hoặc dẫn chiếu tới) các chunk mà
// vector search đã tìm thấy, tối đa 2 bước.
// :name EXPAND_REFERENCES
UNWIND $seed_ids AS seed_id
MATCH (seed:Chunk {chunk_id: seed_id})-[:REFERENCES*1..2]-(c:Chunk)<-[:HAS_CHUNK]-(d:Document)
WHERE NOT c.chunk_id IN $seed_ids
  AND coalesce(d.is_current, true) AND d.duplicate_of IS NULL
  AND ($source_type IS NULL OR d.source_type = $source_type)
  AND ($document_id IS NULL OR d.doc_id = $document_id)
  AND ($roles IS NULL OR any(role IN coalesce(d.allowed_roles, []) WHERE role IN $roles OR role = '*'))
WITH c, d, count(DISTINCT seed) AS matched
RETURN c.chunk_id AS chunk_id, c.text AS content, d.doc_id AS document_id,
       d.title AS title, d.document_type AS document_type,
       d.source_type AS source_type, c.page_start AS page_start,
       c.page_end AS page_end, c.section_path AS section_path,
       matched, 1 AS related, 'references' AS via
ORDER BY matched DESC, c.chunk_index
LIMIT $limit;

// Bước 2b: chunk chia sẻ thực thể "hiếm" (df <= $max_df) với các chunk hạt giống.
// :name EXPAND_SHARED_ENTITIES
UNWIND $seed_ids AS seed_id
MATCH (seed:Chunk {chunk_id: seed_id})-[:MENTIONS]->(e:Entity)
WHERE NOT e.type IN ['dieu_khoan', 'moc_thoi_gian']
  AND count { (e)<-[:MENTIONS]-(:Chunk) } <= $max_df
MATCH (e)<-[m:MENTIONS]-(c:Chunk)<-[:HAS_CHUNK]-(d:Document)
WHERE NOT c.chunk_id IN $seed_ids
  AND coalesce(m.confidence, 1.0) >= $min_confidence
  AND coalesce(d.is_current, true) AND d.duplicate_of IS NULL
  AND ($source_type IS NULL OR d.source_type = $source_type)
  AND ($document_id IS NULL OR d.doc_id = $document_id)
  AND ($roles IS NULL OR any(role IN coalesce(d.allowed_roles, []) WHERE role IN $roles OR role = '*'))
WITH c, d, count(DISTINCT e) AS matched
RETURN c.chunk_id AS chunk_id, c.text AS content, d.doc_id AS document_id,
       d.title AS title, d.document_type AS document_type,
       d.source_type AS source_type, c.page_start AS page_start,
       c.page_end AS page_end, c.section_path AS section_path,
       matched, 2 AS related, 'shared_entity' AS via
ORDER BY matched DESC, c.chunk_index
LIMIT $limit;

// Thực thể gần nghĩa với câu hỏi theo embedding (câu hỏi không gọi đúng tên).
// :name SIMILAR_ENTITIES
CALL db.index.vector.queryNodes('entity_embedding', $k, $vector)
YIELD node, score
WHERE score >= $min_score
RETURN node.name AS name, score
ORDER BY score DESC;

// :name ENTITY_NAMES
MATCH (kb:KnowledgeBase {kb_id: $kb_id})-[:HAS_DOCUMENT]->(:Document)
      -[:HAS_CHUNK]->(:Chunk)-[:MENTIONS]->(e:Entity)
RETURN DISTINCT e.name AS name
ORDER BY name
LIMIT $limit;

// Giá trị đã được chọn sau khi giải quyết mâu thuẫn, kèm các giá trị bị loại.
// :name ATTRIBUTE_VALUES
MATCH (x:Claim {attribute: $attribute})<-[:ASSERTS]-(c:Chunk)<-[:HAS_CHUNK]-(d:Document)
OPTIONAL MATCH (x)-[cf:CONFLICTS_WITH]->(w:Claim)
RETURN x.value AS value, x.unit AS unit, x.status AS status,
       x.confidence AS confidence, x.flags AS flags, x.text AS text,
       c.chunk_id AS chunk_id, c.page_start AS page, c.page_end AS page_end,
       c.section_path AS section_path, d.doc_id AS document_id, d.title AS title,
       d.source_type AS source_type,
       d.effective_date AS effective_date, d.date_source AS date_source, cf.reason AS reason
// Undated claims last: Cypher sorts null first in DESC order.
ORDER BY CASE x.status WHEN 'accepted' THEN 0 ELSE 1 END, coalesce(d.effective_date, '') DESC;

// :name ENTITIES_MISSING_EMBEDDING
MATCH (e:Entity)
WHERE e.embedding IS NULL AND NOT e.type IN ['dieu_khoan', 'moc_thoi_gian']
OPTIONAL MATCH (e)<-[:MENTIONS]-(c:Chunk)
WITH e, collect(c.text)[..3] AS samples
RETURN e.entity_id AS entity_id, e.name AS name, e.type AS type, samples
LIMIT $limit;

// :name SET_ENTITY_ENRICHMENT
UNWIND $rows AS row
MATCH (e:Entity {entity_id: row.entity_id})
SET e.description = row.description, e.embedding = row.embedding;

// :name STATS
MATCH (kb:KnowledgeBase {kb_id: $kb_id})
OPTIONAL MATCH (kb)-[:HAS_DOCUMENT]->(d:Document)
OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
OPTIONAL MATCH (c)-[:MENTIONS]->(e:Entity)
OPTIONAL MATCH (e)-[r:RELATES_TO]-(:Entity)
OPTIONAL MATCH (c)-[ref:REFERENCES]->(:Chunk)
OPTIONAL MATCH (c)-[applies:APPLIES_TO]->(:Entity)
RETURN count(DISTINCT d) AS documents,
       count(DISTINCT c) AS chunks,
       count(DISTINCT e) AS entities,
       count(DISTINCT r) AS relationships,
       count(DISTINCT ref) AS references,
       count(DISTINCT applies) AS applies_to;
