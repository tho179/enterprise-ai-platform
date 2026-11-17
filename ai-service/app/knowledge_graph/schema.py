"""Neo4j schema and Cypher for the KB1/KB2/KB knowledge graph.

The Cypher itself lives in ./cypher/*.cypher (one named block per query) so it
can be read, reviewed and run directly in Neo4j Browser. This module exposes
each block as a module constant, e.g. schema.UPSERT_DOCUMENT.

  01_schema.cypher            constraints, indexes
  02_ingest.cypher            document, chunks, entities, references
  03_merge_and_resolve.cypher KB merge, duplicates, entity resolution, claims
  04_update.cypher            versions, retire, ingest log, deletes
  05_retrieval.cypher         GraphRAG queries
  06_quality.cypher           KB quality metrics
  07_explore.cypher           demo queries (not loaded by name)
"""
from __future__ import annotations

from .cypher_loader import load_queries, split_statements

QUERIES = load_queries()

CONSTRAINTS = split_statements(QUERIES["CONSTRAINTS"])
INDEXES = split_statements(QUERIES["INDEXES"])

REQUIRED = (
    "UPSERT_DOCUMENT", "PROPAGATE_TO_MERGED", "UPSERT_ENTITIES", "UPSERT_REFERENCES",
    "UPSERT_APPLIES_TO", "MERGE_KBS", "RECOMPUTE_RELATION_WEIGHTS", "DELETE_STALE_RELATIONS",
    "RESOLUTION_CANDIDATES", "MANUAL_DECISIONS", "CLEAR_ENTITY_RESOLUTION",
    "WRITE_ENTITY_RESOLUTION", "ALIASES_OF", "DOCUMENT_TEXTS", "CLEAR_DUPLICATES",
    "WRITE_DUPLICATES", "CLEAR_SERIES", "WRITE_SERIES", "CLAIM_SOURCE_CHUNKS",
    "CLEAR_CLAIMS", "WRITE_CLAIMS", "WRITE_CONFLICTS", "FIND_CURRENT",
    "SUPERSEDE_DOCUMENT", "LINK_VERSION", "RETIRE_MISSING", "LOG_RUN",
    "DELETE_DOCUMENT_CHUNKS", "DELETE_DOCUMENT_NODE", "DELETE_EMPTY_DOCUMENT",
    "DELETE_ORPHAN_ENTITIES", "DELETE_ORPHAN_CLAIMS", "GRAPH_CANDIDATES",
    "EXPAND_REFERENCES", "EXPAND_SHARED_ENTITIES", "SIMILAR_ENTITIES", "ENTITY_NAMES",
    "ATTRIBUTE_VALUES", "ENTITIES_MISSING_EMBEDDING", "SET_ENTITY_ENRICHMENT", "STATS",
)
_missing = [name for name in REQUIRED if name not in QUERIES]
if _missing:
    raise RuntimeError(f"Missing Cypher queries: {', '.join(_missing)}")

QUALITY_QUERIES = {name: query for name, query in QUERIES.items() if name.startswith("Q_")}

globals().update({name: QUERIES[name] for name in REQUIRED})
