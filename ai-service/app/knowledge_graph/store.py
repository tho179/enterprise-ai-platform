"""Thin Neo4j adapter used by both the CLI and the FastAPI request path."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from . import schema


class Neo4jStore:
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        from neo4j import GraphDatabase  # lazy: pure functions stay importable

        self.database = database
        self.driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            connection_timeout=3.0,
        )

    def close(self) -> None:
        self.driver.close()

    def verify(self) -> None:
        self.driver.verify_connectivity()

    def _run(self, query: str, **params) -> List[Dict[str, Any]]:
        with self.driver.session(database=self.database) as session:
            return session.execute_write(lambda tx: [dict(row) for row in tx.run(query, **params)])

    def init_schema(self) -> None:
        with self.driver.session(database=self.database) as session:
            for statement in schema.CONSTRAINTS + schema.INDEXES:
                session.run(statement).consume()

    def upsert_record(self, kb_id: str, kb_name: str, record: Dict[str, Any]) -> Dict[str, Any]:
        rows = self._run(
            schema.UPSERT_DOCUMENT,
            kb_id=kb_id,
            kb_name=kb_name,
            doc=record["doc"],
            chunks=record["chunks"],
        )
        self._run(schema.UPSERT_ENTITIES, chunks=record["chunks"])
        self._run(schema.UPSERT_REFERENCES, chunks=record["chunks"])
        self._run(schema.UPSERT_APPLIES_TO, chunks=record["chunks"])
        return rows[0] if rows else {"doc_id": record["doc"]["doc_id"], "chunks": 0}

    def merge_kbs(self, sources: Iterable[str], target: str, target_name: str = "KB hợp nhất") -> int:
        rows = self._run(
            schema.MERGE_KBS,
            sources=list(sources),
            target=target,
            target_name=target_name,
        )
        return int(rows[0]["documents"]) if rows else 0

    def find_current(self, source_uri: str) -> Optional[Dict[str, Any]]:
        rows = self._run(schema.FIND_CURRENT, source_uri=source_uri)
        return rows[0]["doc"] if rows else None

    def supersede(self, source_uri: str) -> Optional[str]:
        rows = self._run(schema.SUPERSEDE_DOCUMENT, source_uri=source_uri)
        return rows[0]["old_doc_id"] if rows else None

    def link_version(self, old_doc_id: str, new_doc_id: str) -> None:
        self._run(schema.LINK_VERSION, old_doc_id=old_doc_id, new_doc_id=new_doc_id)

    def graph_candidates(
        self,
        names: Iterable[str],
        kb_ids: Iterable[str],
        limit: int = 10,
        source_type: Optional[str] = None,
        document_id: Optional[str] = None,
        allowed_roles: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        return self._run(
            schema.GRAPH_CANDIDATES,
            names=list(names),
            kb_ids=list(kb_ids),
            limit=limit,
            source_type=source_type,
            document_id=document_id,
            roles=allowed_roles,
        )

    def expand_from_chunks(
        self,
        seed_ids: Iterable[str],
        limit: int = 10,
        source_type: Optional[str] = None,
        document_id: Optional[str] = None,
        allowed_roles: Optional[List[str]] = None,
        max_entity_df: int = 25,
    ) -> List[Dict[str, Any]]:
        """1-2 hops from chunks found by vector search."""
        params = {
            "seed_ids": list(seed_ids),
            "limit": limit,
            "source_type": source_type,
            "document_id": document_id,
            "roles": allowed_roles,
        }
        return [
            *self._run(schema.EXPAND_REFERENCES, **params),
            *self._run(schema.EXPAND_SHARED_ENTITIES, max_df=max_entity_df, **params),
        ]

    def similar_entities(self, vector: List[float], min_score: float, k: int = 5) -> List[str]:
        rows = self._run(schema.SIMILAR_ENTITIES, vector=vector, min_score=min_score, k=k)
        return [row["name"] for row in rows if row.get("name")]

    def entities_missing_embedding(self, limit: int = 128) -> List[Dict[str, Any]]:
        return self._run(schema.ENTITIES_MISSING_EMBEDDING, limit=limit)

    def set_entity_enrichment(self, rows: List[Dict[str, Any]]) -> None:
        self._run(schema.SET_ENTITY_ENRICHMENT, rows=rows)

    def entity_names(self, kb_id: str, limit: int = 5000) -> List[str]:
        rows = self._run(schema.ENTITY_NAMES, kb_id=kb_id, limit=limit)
        return [row["name"] for row in rows if row.get("name")]

    def delete_document(self, document_id: str, version_id: Optional[str] = None) -> int:
        rows = self._run(
            schema.DELETE_DOCUMENT_CHUNKS,
            document_id=document_id,
            version_id=version_id,
        )
        deleted = int(rows[0]["deleted"]) if rows else 0
        if version_id is None:
            self._run(schema.DELETE_DOCUMENT_NODE, document_id=document_id)
        else:
            # Deleting the last version must not leave an empty Document node.
            self._run(schema.DELETE_EMPTY_DOCUMENT, document_id=document_id)
        self._run(schema.DELETE_ORPHAN_ENTITIES)
        return deleted

    def stats(self, kb_id: str) -> Dict[str, int]:
        rows = self._run(schema.STATS, kb_id=kb_id)
        return {key: int(value) for key, value in (rows[0] if rows else {}).items()}

    def sample(self, kb_id: str, chunk_limit: int = 5) -> Dict[str, Any]:
        docs = self._run(
            """
            MATCH (kb:KnowledgeBase {kb_id: $kb_id})-[:HAS_DOCUMENT]->(d:Document)
            RETURN d { .doc_id, .title, .source_uri, .source_type, .content_hash,
                       .page_count, .version, .is_current } AS doc
            ORDER BY d.title LIMIT 3
            """,
            kb_id=kb_id,
        )
        chunks = self._run(
            """
            MATCH (kb:KnowledgeBase {kb_id: $kb_id})-[:HAS_DOCUMENT]->(d:Document)
                  -[:HAS_CHUNK]->(c:Chunk)
            RETURN c { .chunk_id, .chunk_index, .text, .page_start, .page_end,
                       .section_path } AS chunk, d.title AS title
            ORDER BY d.title, c.chunk_index LIMIT $limit
            """,
            kb_id=kb_id,
            limit=chunk_limit,
        )
        entities = self._run(
            """
            MATCH (kb:KnowledgeBase {kb_id: $kb_id})-[:HAS_DOCUMENT]->(:Document)
                  -[:HAS_CHUNK]->(:Chunk)-[:MENTIONS]->(e:Entity)
            RETURN DISTINCT e { .entity_id, .name, .type } AS entity
            ORDER BY entity.type, entity.name LIMIT 20
            """,
            kb_id=kb_id,
        )
        return {
            "kb": kb_id,
            "documents": [row["doc"] for row in docs],
            "chunks": [{**row["chunk"], "document_title": row["title"]} for row in chunks],
            "entities": [row["entity"] for row in entities],
            "stats": self.stats(kb_id),
        }
