"""Rebuild every derived graph edge from the Chunk nodes already in Neo4j.

Entities, MENTIONS, RELATES_TO, REFERENCES and APPLIES_TO are all derived from
chunk text, so they can be dropped and recomputed after a rule change. Documents
and chunks are left untouched.
"""
from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.embedding_service import EmbeddingService  # noqa: E402
from app.knowledge_graph import schema  # noqa: E402
from app.knowledge_graph.enrich import enrich_entities  # noqa: E402
from app.knowledge_graph.extract import extract_entities, link_chunks  # noqa: E402
from app.knowledge_graph.pipeline import KB  # noqa: E402
from app.knowledge_graph.service import get_store  # noqa: E402

BATCH = 200


def main() -> int:
    store = get_store()
    rows = store._run(
        """
        MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)
        RETURN d.doc_id AS doc_id, c.chunk_id AS chunk_id, c.text AS text,
               c.section_path AS section_path
        """
    )
    by_document = defaultdict(list)
    for row in rows:
        text = row.get("text") or ""
        by_document[row["doc_id"]].append(
            {
                "chunk_id": row["chunk_id"],
                "text": text,
                "section_path": list(row.get("section_path") or []),
                "entities": extract_entities(text),
            }
        )

    chunks = []
    for items in by_document.values():
        link_chunks(items)
        chunks.extend(items)

    store._run("MATCH ()-[r:MENTIONS|RELATES_TO|REFERENCES|APPLIES_TO]->() DELETE r")
    store._run("MATCH (e:Entity) DETACH DELETE e")
    for start in range(0, len(chunks), BATCH):
        batch = chunks[start:start + BATCH]
        store._run(schema.UPSERT_ENTITIES, chunks=batch)
        store._run(schema.UPSERT_REFERENCES, chunks=batch)
        store._run(schema.UPSERT_APPLIES_TO, chunks=batch)

    enriched = enrich_entities(store, EmbeddingService())
    print(f"Rebuilt {len(chunks)} chunks | enriched {enriched} entities | {store.stats(KB)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
