"""Rebuild every derived graph edge from the Chunk nodes already in Neo4j.

Entities, MENTIONS, RELATES_TO, REFERENCES and APPLIES_TO are all derived from
chunk text, so they can be dropped and recomputed after a rule change. Documents
and chunks are kept; only their derived properties (source_trust,
effective_date) are refreshed. Reviewer decisions (SAME_AS/NOT_SAME_AS with
method='manual') are saved by entity name and restored afterwards.

This is the KB update path for an *extractor* change, as opposed to a source
change (scripts/10_build_neo4j_kb.py --update).
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
from app.knowledge_graph.extract import (  # noqa: E402
    SOURCE_TRUST,
    effective_date,
    extract_entities,
    link_chunks,
)
from app.knowledge_graph.pipeline import KB  # noqa: E402
from app.knowledge_graph.service import get_store  # noqa: E402

BATCH = 200


def main() -> int:
    store = get_store()
    rows = store._run(
        """
        MATCH (d:Document)-[:HAS_CHUNK]->(c:Chunk)
        RETURN d.doc_id AS doc_id, d.title AS title, d.source_type AS source_type,
               c.chunk_id AS chunk_id, c.text AS text, c.chunk_index AS chunk_index,
               c.section_path AS section_path
        ORDER BY d.doc_id, c.chunk_index
        """
    )
    manual = store._run(
        """
        MATCH (a:Entity)-[r:SAME_AS|NOT_SAME_AS|POSSIBLY_SAME_AS]->(b:Entity)
        WHERE r.method = 'manual'
        RETURN a.name AS a_name, a.type AS a_type, b.name AS b_name, b.type AS b_type,
               type(r) AS relation
        """
    )
    by_document = defaultdict(list)
    documents = {}
    for row in rows:
        documents.setdefault(row["doc_id"], {
            "doc_id": row["doc_id"],
            "title": row.get("title") or "",
            "source_type": row.get("source_type"),
            "head": [],
        })["head"].append(row.get("text") or "")
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

    store._run(
        """
        UNWIND $docs AS doc
        MATCH (d:Document {doc_id: doc.doc_id})
        SET d.source_trust = doc.source_trust, d.effective_date = doc.effective_date,
            d.date_source = doc.date_source
        """,
        docs=[
            {
                "doc_id": doc["doc_id"],
                "source_trust": SOURCE_TRUST.get(doc["source_type"], 0.5),
                "effective_date": date,
                "date_source": source,
            }
            for doc in documents.values()
            for date, source in [effective_date(doc["title"], "\n".join(doc["head"][:3]))]
        ],
    )
    for decision in manual:
        store._run(
            f"""
            MATCH (a:Entity {{name: $a_name, type: $a_type}})
            MATCH (b:Entity {{name: $b_name, type: $b_type}})
            MERGE (a)-[r:{decision["relation"]}]->(b)
            SET r.method = 'manual'
            """,
            **{key: value for key, value in decision.items() if key != "relation"},
        )

    enriched = enrich_entities(store, EmbeddingService())
    print(f"Rebuilt {len(chunks)} chunks | enriched {enriched} entities | {store.stats(KB)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
