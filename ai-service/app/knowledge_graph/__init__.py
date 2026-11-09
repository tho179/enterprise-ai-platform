"""Reference implementation of the EAKWP knowledge-graph layer.

  - pure builders (extract.py) can run without Neo4j;
  - the Neo4j adapter (store.py) is used by the CLI and the ingest/chat path;
  - pipeline.py wires KB1 (PDF), KB2 (links), merge and graph retrieval;
  - service.py syncs backend chunks and fuses graph hits into RAG.
"""
from .pipeline import KB, KB1, KB2, graph_context, load_links, load_pdf, merge, rrf_fuse

__all__ = ["KB", "KB1", "KB2", "graph_context", "load_links", "load_pdf", "merge", "rrf_fuse"]
