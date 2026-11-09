"""Neo4j schema and Cypher for the KB1/KB2/KB prototype.

The model is a labelled property graph:
  KnowledgeBase -HAS_DOCUMENT-> Document -HAS_CHUNK-> Chunk -MENTIONS-> Entity
  Chunk -REFERENCES-> Chunk      a clause citing another clause of its document
  Chunk -APPLIES_TO-> Entity     the entity is the subject of the chunk's section
  Entity -RELATES_TO- Entity     co-mentioned in a chunk
Documents/chunks/entities use content-addressed IDs, so the same source can
belong to KB1 and KB2 without duplicating nodes.
"""
from __future__ import annotations

CONSTRAINTS = [
    "CREATE CONSTRAINT kb_id IF NOT EXISTS FOR (k:KnowledgeBase) REQUIRE k.kb_id IS UNIQUE",
    "CREATE CONSTRAINT doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.doc_id IS UNIQUE",
    "CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE",
    "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE",
]

INDEXES = [
    "CREATE INDEX doc_title IF NOT EXISTS FOR (d:Document) ON (d.title)",
    "CREATE INDEX doc_source IF NOT EXISTS FOR (d:Document) ON (d.source_uri)",
    "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)",
    "CREATE INDEX chunk_version IF NOT EXISTS FOR (c:Chunk) ON (c.version_id)",
    """
    CREATE VECTOR INDEX entity_embedding IF NOT EXISTS
    FOR (e:Entity) ON (e.embedding)
    OPTIONS {indexConfig: {`vector.dimensions`: 384, `vector.similarity_function`: 'cosine'}}
    """,
]

UPSERT_DOCUMENT = """
MERGE (kb:KnowledgeBase {kb_id: $kb_id})
  ON CREATE SET kb.name = $kb_name, kb.created_at = datetime()
WITH kb
MERGE (d:Document {doc_id: $doc.doc_id})
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
RETURN d.doc_id AS doc_id, size($chunks) AS chunks
"""

UPSERT_ENTITIES = """
UNWIND $chunks AS c
MATCH (ch:Chunk {chunk_id: c.chunk_id})
UNWIND c.entities AS e
MERGE (en:Entity {entity_id: e.entity_id})
  ON CREATE SET en.name = e.name, en.type = e.type
MERGE (ch)-[:MENTIONS]->(en)
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
  ON CREATE SET r.kind = 'co_mentions', r.weight = 1
"""

UPSERT_REFERENCES = """
UNWIND $chunks AS c
UNWIND c.references AS ref
MATCH (source:Chunk {chunk_id: c.chunk_id})
MATCH (target:Chunk {chunk_id: ref.target})
MERGE (source)-[r:REFERENCES]->(target)
SET r.article = ref.article
"""

UPSERT_APPLIES_TO = """
UNWIND $chunks AS c
UNWIND c.applies_to AS entity_id
MATCH (chunk:Chunk {chunk_id: c.chunk_id})
MATCH (entity:Entity {entity_id: entity_id})
MERGE (chunk)-[:APPLIES_TO]->(entity)
"""

MERGE_KBS = """
MERGE (target:KnowledgeBase {kb_id: $target})
  ON CREATE SET target.name = $target_name, target.created_at = datetime()
WITH target
UNWIND $sources AS sid
MATCH (src:KnowledgeBase {kb_id: sid})
MERGE (src)-[:MERGED_INTO]->(target)
WITH DISTINCT target
MATCH (src:KnowledgeBase)-[:HAS_DOCUMENT]->(d:Document)
WHERE src.kb_id IN $sources
MERGE (target)-[:HAS_DOCUMENT]->(d)
RETURN count(DISTINCT d) AS documents
"""

SUPERSEDE_DOCUMENT = """
MATCH (d:Document {source_uri: $source_uri, is_current: true})
SET d.is_current = false, d.superseded_at = datetime()
RETURN d.doc_id AS old_doc_id
ORDER BY d.version DESC
LIMIT 1
"""

LINK_VERSION = """
MATCH (old:Document {doc_id: $old_doc_id})
MATCH (new:Document {doc_id: $new_doc_id})
MERGE (new)-[:NEW_VERSION_OF]->(old)
"""

FIND_CURRENT = """
MATCH (d:Document {source_uri: $source_uri, is_current: true})
RETURN d { .doc_id, .content_hash, .version } AS doc
ORDER BY d.version DESC
LIMIT 1
"""

_ACCESS_FILTER = """
  ($source_type IS NULL OR d.source_type = $source_type)
  AND ($document_id IS NULL OR d.doc_id = $document_id)
  AND ($roles IS NULL OR any(role IN coalesce(d.allowed_roles, []) WHERE role IN $roles OR role = '*'))
"""

_HIT_COLUMNS = """
       c.chunk_id AS chunk_id,
       c.text AS content,
       d.doc_id AS document_id,
       d.title AS title,
       d.document_type AS document_type,
       d.source_type AS source_type,
       c.page_start AS page_start,
       c.page_end AS page_end,
       c.section_path AS section_path
"""

# A numbered entity ("Điều 5") must not hop to neighbours: it is shared by
# unrelated documents, so its co-mentions are noise.
GRAPH_CANDIDATES = f"""
MATCH (seed:Entity)
WHERE seed.name IN $names
MATCH (seed)-[:RELATES_TO*0..1]-(e:Entity)<-[:MENTIONS]-(c:Chunk)<-[:HAS_CHUNK]-(d:Document)
MATCH (kb:KnowledgeBase)-[:HAS_DOCUMENT]->(d)
WHERE kb.kb_id IN $kb_ids
  AND (seed = e OR NOT seed.type IN ['dieu_khoan', 'moc_thoi_gian'])
  AND {_ACCESS_FILTER}
WITH c, d,
     count(DISTINCT CASE WHEN seed = e THEN seed END) AS matched,
     count(DISTINCT CASE WHEN seed <> e THEN e END) AS related,
     count {{ (c)-[:APPLIES_TO]->(x:Entity) WHERE x.name IN $names }} AS heading_matches
WITH c, d, matched + heading_matches AS matched, related
WHERE matched > 0 OR related > 0
RETURN {_HIT_COLUMNS},
       matched,
       related,
       'entity' AS via
ORDER BY matched DESC, related ASC, c.chunk_index
LIMIT $limit
"""

# Clauses cited by, or citing, the chunks vector search already found.
EXPAND_REFERENCES = f"""
UNWIND $seed_ids AS seed_id
MATCH (seed:Chunk {{chunk_id: seed_id}})-[:REFERENCES*1..2]-(c:Chunk)<-[:HAS_CHUNK]-(d:Document)
WHERE NOT c.chunk_id IN $seed_ids
  AND {_ACCESS_FILTER}
WITH c, d, count(DISTINCT seed) AS matched
RETURN {_HIT_COLUMNS},
       matched,
       1 AS related,
       'references' AS via
ORDER BY matched DESC, c.chunk_index
LIMIT $limit
"""

# Chunks sharing a specific entity with those chunks; ubiquitous ones are skipped.
EXPAND_SHARED_ENTITIES = f"""
UNWIND $seed_ids AS seed_id
MATCH (seed:Chunk {{chunk_id: seed_id}})-[:MENTIONS]->(e:Entity)
WHERE NOT e.type IN ['dieu_khoan', 'moc_thoi_gian']
  AND count {{ (e)<-[:MENTIONS]-(:Chunk) }} <= $max_df
MATCH (e)<-[:MENTIONS]-(c:Chunk)<-[:HAS_CHUNK]-(d:Document)
WHERE NOT c.chunk_id IN $seed_ids
  AND {_ACCESS_FILTER}
WITH c, d, count(DISTINCT e) AS matched
RETURN {_HIT_COLUMNS},
       matched,
       2 AS related,
       'shared_entity' AS via
ORDER BY matched DESC, c.chunk_index
LIMIT $limit
"""

SIMILAR_ENTITIES = """
CALL db.index.vector.queryNodes('entity_embedding', $k, $vector)
YIELD node, score
WHERE score >= $min_score
RETURN node.name AS name, score
ORDER BY score DESC
"""

ENTITIES_MISSING_EMBEDDING = """
MATCH (e:Entity)
WHERE e.embedding IS NULL AND NOT e.type IN ['dieu_khoan', 'moc_thoi_gian']
OPTIONAL MATCH (e)<-[:MENTIONS]-(c:Chunk)
WITH e, collect(c.text)[..3] AS samples
RETURN e.entity_id AS entity_id, e.name AS name, e.type AS type, samples
LIMIT $limit
"""

SET_ENTITY_ENRICHMENT = """
UNWIND $rows AS row
MATCH (e:Entity {entity_id: row.entity_id})
SET e.description = row.description, e.embedding = row.embedding
"""

ENTITY_NAMES = """
MATCH (kb:KnowledgeBase {kb_id: $kb_id})-[:HAS_DOCUMENT]->(:Document)
      -[:HAS_CHUNK]->(:Chunk)-[:MENTIONS]->(e:Entity)
RETURN DISTINCT e.name AS name
ORDER BY name
LIMIT $limit
"""

DELETE_DOCUMENT_CHUNKS = """
MATCH (d:Document {doc_id: $document_id})-[:HAS_CHUNK]->(c:Chunk)
WHERE $version_id IS NULL OR c.version_id = $version_id
WITH collect(c) AS chunks
WITH chunks, size(chunks) AS total
FOREACH (chunk IN chunks | DETACH DELETE chunk)
RETURN total AS deleted
"""

DELETE_DOCUMENT_NODE = """
MATCH (d:Document {doc_id: $document_id})
DETACH DELETE d
"""

DELETE_EMPTY_DOCUMENT = """
MATCH (d:Document {doc_id: $document_id})
WHERE NOT (d)-[:HAS_CHUNK]->(:Chunk)
DETACH DELETE d
RETURN count(d) AS deleted
"""

DELETE_ORPHAN_ENTITIES = """
MATCH (e:Entity)
WHERE NOT (e)<-[:MENTIONS]-(:Chunk)
DETACH DELETE e
RETURN count(e) AS deleted
"""

STATS = """
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
       count(DISTINCT applies) AS applies_to
"""
