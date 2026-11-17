// =====================================================================
// 03_merge_and_resolve.cypher - Gộp KB1 + KB2 -> KB và xử lý các vấn đề
// phát sinh khi tích hợp nhiều nguồn:
//   (1) trùng lặp tài liệu       -> DUPLICATE_OF
//   (2) cùng thực thể, khác tên  -> SAME_AS / POSSIBLY_SAME_AS (hợp nhất mờ)
//   (3) nhiều phiên bản một văn bản -> NEW_VERSION_OF (chuỗi văn bản)
//   (4) dữ kiện mâu thuẫn        -> Claim + CONFLICTS_WITH
//   (5) độ tin cậy quan hệ        -> RELATES_TO.weight / confidence
// Logic quyết định (ngưỡng, luật ưu tiên) nằm ở resolve.py/consistency.py;
// các truy vấn ở đây chỉ đọc dữ liệu đầu vào và ghi kết quả.
// =====================================================================

// :name MERGE_KBS
MERGE (target:KnowledgeBase {kb_id: $target})
  ON CREATE SET target.name = $target_name, target.created_at = datetime()
SET target.updated_at = datetime()
WITH target
UNWIND $sources AS sid
MATCH (src:KnowledgeBase {kb_id: sid})
MERGE (src)-[:MERGED_INTO]->(target)
WITH DISTINCT target
MATCH (src:KnowledgeBase)-[:HAS_DOCUMENT]->(d:Document)
WHERE src.kb_id IN $sources
MERGE (target)-[:HAS_DOCUMENT]->(d)
RETURN count(DISTINCT d) AS documents;

// ---------------------------------------------------------------------
// (5) Trọng số quan hệ đồng xuất hiện: weight = số chunk nhắc cả hai,
// confidence = Jaccard(chunk(a), chunk(b)). Tính lại toàn bộ nên idempotent.
// :name RECOMPUTE_RELATION_WEIGHTS
MATCH (a:Entity)-[r:RELATES_TO]-(b:Entity)
WHERE a.entity_id < b.entity_id
WITH a, b, r,
     COUNT { (a)<-[:MENTIONS]-(:Chunk)-[:MENTIONS]->(b) } AS together,
     COUNT { (a)<-[:MENTIONS]-(:Chunk) } AS na,
     COUNT { (b)<-[:MENTIONS]-(:Chunk) } AS nb
SET r.weight = together,
    r.confidence = CASE WHEN na + nb - together <= 0 THEN 0.0
                        ELSE round(toFloat(together) / (na + nb - together), 4) END
RETURN count(r) AS relationships, round(avg(r.confidence), 4) AS avg_confidence;

// :name DELETE_STALE_RELATIONS
MATCH (:Entity)-[r:RELATES_TO]-(:Entity)
WHERE r.weight = 0
DELETE r
RETURN count(r) AS deleted;

// ---------------------------------------------------------------------
// (2) Hợp nhất thực thể mờ. Python tính điểm giống nhau rồi ghi lại.
// Quyết định thủ công (method = 'manual') không bao giờ bị ghi đè.
// :name RESOLUTION_CANDIDATES
MATCH (e:Entity)
WHERE e.type IN $types AND (e)<-[:MENTIONS]-(:Chunk)
RETURN e.entity_id AS entity_id, e.name AS name, e.type AS type,
       COUNT { (e)<-[:MENTIONS]-(:Chunk) } AS mentions;

// :name MANUAL_DECISIONS
MATCH (a:Entity)-[r:SAME_AS|POSSIBLY_SAME_AS|NOT_SAME_AS]-(b:Entity)
WHERE r.method = 'manual' AND a.entity_id < b.entity_id
RETURN a.entity_id AS a, b.entity_id AS b, type(r) AS relation;

// :name CLEAR_ENTITY_RESOLUTION
MATCH (:Entity)-[r:SAME_AS|POSSIBLY_SAME_AS]-(:Entity)
WHERE coalesce(r.method, '') <> 'manual'
DELETE r
RETURN count(r) AS deleted;

// :name WRITE_ENTITY_RESOLUTION
UNWIND $pairs AS p
MATCH (a:Entity {entity_id: p.a})
MATCH (b:Entity {entity_id: p.b})
FOREACH (_ IN CASE WHEN p.relation = 'SAME_AS' THEN [1] ELSE [] END |
  MERGE (a)-[r:SAME_AS]-(b)
  SET r.score = p.score, r.membership = p.membership, r.method = p.method)
FOREACH (_ IN CASE WHEN p.relation = 'POSSIBLY_SAME_AS' THEN [1] ELSE [] END |
  MERGE (a)-[r:POSSIBLY_SAME_AS]-(b)
  SET r.score = p.score, r.membership = p.membership, r.method = p.method)
RETURN count(*) AS written;

// Tên đồng nghĩa của các thực thể trong câu hỏi, dùng khi truy xuất.
// :name ALIASES_OF
UNWIND $names AS name
MATCH (:Entity {name: name})-[:SAME_AS]-(alias:Entity)
RETURN DISTINCT alias.name AS name;

// ---------------------------------------------------------------------
// (1) + (3) Trùng lặp và chuỗi phiên bản: đọc nội dung tài liệu hiện hành.
// :name DOCUMENT_TEXTS
MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)
WITH d, c ORDER BY c.chunk_index
RETURN d.doc_id AS doc_id, d.title AS title, d.source_type AS source_type,
       d.source_uri AS source_uri, coalesce(d.source_trust, 0.5) AS source_trust,
       d.effective_date AS effective_date, coalesce(d.is_current, true) AS is_current,
       d.superseded_reason AS superseded_reason, collect(c.text) AS texts;

// :name CLEAR_DUPLICATES
MATCH (d:Document)
WHERE d.duplicate_of IS NOT NULL OR (d)-[:DUPLICATE_OF|SIMILAR_TO]->()
OPTIONAL MATCH (d)-[r:DUPLICATE_OF|SIMILAR_TO]->()
DELETE r
REMOVE d.duplicate_of
RETURN count(DISTINCT d) AS cleared;

// DUPLICATE_OF ẩn bản trùng khỏi truy xuất (duplicate_of); SIMILAR_TO chỉ
// ghi nhận hai tài liệu có phần lớn nội dung chung (phiên bản, phụ lục).
// :name WRITE_DUPLICATES
UNWIND $pairs AS p
MATCH (dup:Document {doc_id: p.duplicate})
MATCH (keep:Document {doc_id: p.keep})
FOREACH (_ IN CASE WHEN p.relation = 'DUPLICATE_OF' THEN [1] ELSE [] END |
  MERGE (dup)-[r:DUPLICATE_OF]->(keep)
  SET r.overlap = p.overlap, r.reason = p.reason, dup.duplicate_of = keep.doc_id)
FOREACH (_ IN CASE WHEN p.relation = 'SIMILAR_TO' THEN [1] ELSE [] END |
  MERGE (dup)-[r:SIMILAR_TO]->(keep)
  SET r.overlap = p.overlap, r.reason = p.reason)
RETURN count(*) AS written;

// :name CLEAR_SERIES
MATCH (new:Document)-[r:NEW_VERSION_OF {method: 'series'}]->(old:Document)
DELETE r
WITH DISTINCT old
WHERE old.superseded_reason = 'series'
SET old.is_current = true
REMOVE old.superseded_by, old.superseded_reason, old.superseded_at
RETURN count(old) AS restored;

// :name WRITE_SERIES
UNWIND $links AS l
MATCH (new:Document {doc_id: l.new})
MATCH (old:Document {doc_id: l.old})
MERGE (new)-[r:NEW_VERSION_OF]->(old)
SET r.method = 'series', r.series = l.series,
    old.is_current = false, old.superseded_by = new.doc_id,
    old.superseded_reason = 'series', old.superseded_at = datetime()
RETURN count(r) AS written;

// ---------------------------------------------------------------------
// (4) Dữ kiện và mâu thuẫn. Claim là một khẳng định có giá trị số
// ("Vốn điều lệ = 10.623.648.220.000 đồng") gắn với chunk nguồn.
// :name CLAIM_SOURCE_CHUNKS
MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)
WHERE any(k IN $keywords WHERE toLower(c.text) CONTAINS k)
RETURN c.chunk_id AS chunk_id, c.text AS text, c.page_start AS page,
       d.doc_id AS doc_id, d.title AS title, d.source_type AS source_type,
       coalesce(d.source_trust, 0.5) AS source_trust,
       coalesce(d.is_current, true) AS is_current,
       d.duplicate_of AS duplicate_of, d.effective_date AS effective_date;

// :name CLEAR_CLAIMS
MATCH (x:Claim)
DETACH DELETE x
RETURN count(x) AS deleted;

// :name WRITE_CLAIMS
UNWIND $claims AS cl
MATCH (ch:Chunk {chunk_id: cl.chunk_id})
MERGE (x:Claim {claim_id: cl.claim_id})
SET x.attribute = cl.attribute, x.value = cl.value, x.unit = cl.unit,
    x.text = cl.text, x.confidence = cl.confidence, x.flags = cl.flags,
    x.status = cl.status, x.doc_id = cl.doc_id,
    x.effective_date = cl.effective_date
MERGE (ch)-[:ASSERTS]->(x)
WITH x, cl
OPTIONAL MATCH (e:Entity {entity_id: cl.entity_id})
FOREACH (_ IN CASE WHEN e IS NULL THEN [] ELSE [1] END | MERGE (x)-[:ABOUT]->(e))
RETURN count(x) AS written;

// Hướng cạnh: claim bị loại -> claim được chọn.
// :name WRITE_CONFLICTS
UNWIND $conflicts AS cf
MATCH (loser:Claim {claim_id: cf.loser})
MATCH (winner:Claim {claim_id: cf.winner})
MERGE (loser)-[r:CONFLICTS_WITH]->(winner)
SET r.resolution = cf.resolution, r.reason = cf.reason
RETURN count(r) AS written;
