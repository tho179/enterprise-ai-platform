// =====================================================================
// 01_schema.cypher - Lược đồ đồ thị tri thức EAKWP (Neo4j 5, LPG)
//
//   (:KnowledgeBase)-[:HAS_DOCUMENT]->(:Document)-[:HAS_CHUNK]->(:Chunk)
//   (:Chunk)-[:MENTIONS {confidence, method}]->(:Entity)
//   (:Chunk)-[:APPLIES_TO]->(:Entity)        thực thể là chủ đề của mục
//   (:Chunk)-[:REFERENCES]->(:Chunk)         điều khoản dẫn chiếu điều khoản
//   (:Entity)-[:RELATES_TO {weight, confidence}]-(:Entity)   đồng xuất hiện
//   (:Entity)-[:SAME_AS | POSSIBLY_SAME_AS {score}]-(:Entity) hợp nhất mờ
//   (:Document)-[:NEW_VERSION_OF]->(:Document)                phiên bản
//   (:Document)-[:DUPLICATE_OF {overlap}]->(:Document)        trùng nội dung
//   (:Chunk)-[:ASSERTS]->(:Claim)-[:ABOUT]->(:Entity)         dữ kiện số
//   (:Claim)-[:CONFLICTS_WITH {resolution}]->(:Claim)         mâu thuẫn
//   (:IngestRun)                                              nhật ký cập nhật
//
// Chạy bằng: cypher-shell -f 01_schema.cypher, hoặc store.init_schema().
// Mỗi khối "// :name X" là một truy vấn có tên được Python nạp theo tên.
// =====================================================================

// :name CONSTRAINTS
CREATE CONSTRAINT kb_id IF NOT EXISTS FOR (k:KnowledgeBase) REQUIRE k.kb_id IS UNIQUE;
CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE;
CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE;
CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE;
CREATE CONSTRAINT claim_id IF NOT EXISTS FOR (c:Claim) REQUIRE c.claim_id IS UNIQUE;
CREATE CONSTRAINT run_id IF NOT EXISTS FOR (r:IngestRun) REQUIRE r.run_id IS UNIQUE;

// :name INDEXES
CREATE INDEX doc_title IF NOT EXISTS FOR (d:Document) ON (d.title);
CREATE INDEX doc_source IF NOT EXISTS FOR (d:Document) ON (d.source_uri);
CREATE INDEX doc_current IF NOT EXISTS FOR (d:Document) ON (d.is_current);
CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE INDEX chunk_version IF NOT EXISTS FOR (c:Chunk) ON (c.version_id);
CREATE INDEX claim_attribute IF NOT EXISTS FOR (c:Claim) ON (c.attribute);
CREATE VECTOR INDEX entity_embedding IF NOT EXISTS
FOR (e:Entity) ON (e.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}};
