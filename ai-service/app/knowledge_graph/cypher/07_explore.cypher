// =====================================================================
// 07_explore.cypher - Truy vấn minh họa để chạy trong Neo4j Browser
// (http://localhost:7474). Không được code nạp; dùng để xem và chụp hình.
// =====================================================================

// 1. Toàn cảnh: KB hợp nhất và các KB nguồn
MATCH p = (src:KnowledgeBase)-[:MERGED_INTO]->(kb:KnowledgeBase {kb_id: 'KB'})
RETURN p;

// 2. Một tài liệu với chunk và thực thể (giới hạn 25 chunk)
MATCH (d:Document {title: 'Quy che hoat dong HDQT'})-[:HAS_CHUNK]->(c:Chunk)
WITH d, c ORDER BY c.chunk_index LIMIT 25
OPTIONAL MATCH p = (c)-[:MENTIONS]->(e:Entity)
WHERE NOT e.type IN ['dieu_khoan', 'moc_thoi_gian']
RETURN d, c, p;

// 3. Láng giềng của một thực thể qua quan hệ đồng xuất hiện mạnh
MATCH p = (e:Entity {name: 'Hội đồng Quản trị'})-[r:RELATES_TO]-(n:Entity)
WHERE r.confidence >= 0.1
RETURN p ORDER BY r.confidence DESC LIMIT 20;

// 4. Chuỗi phiên bản của Điều lệ
MATCH p = (:Document)-[:NEW_VERSION_OF*1..]->(:Document)
RETURN p;

// 5. Tài liệu trùng lặp giữa hai đường nạp (PDF offline và upload)
MATCH p = (:Document)-[:DUPLICATE_OF]->(:Document)
RETURN p;

// 6. Mâu thuẫn dữ kiện: vốn điều lệ theo từng nguồn
MATCH (x:Claim {attribute: 'Vốn điều lệ'})<-[:ASSERTS]-(:Chunk)<-[:HAS_CHUNK]-(d:Document)
OPTIONAL MATCH (x)-[cf:CONFLICTS_WITH]->(w:Claim)
RETURN d.title AS nguon, d.effective_date AS hieu_luc, x.value AS gia_tri,
       x.status AS trang_thai, x.flags AS canh_bao, cf.reason AS ly_do
ORDER BY hieu_luc;

// 7. Cặp thực thể chờ người duyệt (hợp nhất mờ chưa chắc chắn)
MATCH (a:Entity)-[r:POSSIBLY_SAME_AS]->(b:Entity)
RETURN a.name, b.name, r.score, r.membership
ORDER BY r.score DESC;

// 8. Duyệt thủ công: chấp nhận một cặp (thay tên cho phù hợp)
// MATCH (a:Entity {name: 'X'})-[r:POSSIBLY_SAME_AS]-(b:Entity {name: 'Y'})
// DELETE r MERGE (a)-[:SAME_AS {method: 'manual', score: 1.0}]-(b);

// 9. Nhật ký cập nhật KB
MATCH (r:IngestRun)-[:UPDATED]->(kb)
RETURN r.finished_at, kb.kb_id, r.source, r.inserted, r.skipped,
       r.new_version, r.retired, r.failed
ORDER BY r.finished_at DESC LIMIT 10;
