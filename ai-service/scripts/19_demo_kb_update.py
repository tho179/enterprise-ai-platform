"""Demonstrate the KB update mechanism end to end on a sandbox KB.

Scenario (one file name, its content changes over time):
  1. insert       Phu_luc_demo.pdf = amendment 2 (2022, charter capital 7.274 bn)
  2. skip         same file loaded again: content hash unchanged
  3. new_version  file replaced by amendment 5.1 (2024, 7.355 bn)
  4. retrieval    graph search over the sandbox KB only returns the new version
  5. retire       file deleted from the folder, --prune marks it historical
Each step is logged as an IngestRun. The sandbox KB (KB_DEMO) is not merged
into KB, so the production KB is untouched; everything is removed at the end
unless --keep is given.

  docker compose exec ai-service python scripts/19_demo_kb_update.py
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.knowledge_graph.pipeline import load_pdf_folder  # noqa: E402
from app.knowledge_graph.service import get_store  # noqa: E402

KB_DEMO = "KB_DEMO"
SOURCES = ROOT / "data" / "documents" / "dieu_le_sua_doi"
V1 = SOURCES / "Phu_luc_sua_doi_dieu_le_lan_2.pdf"
V2 = SOURCES / "Phu_luc_sua_doi_dieu_le_lan_5_1.pdf"
SANDBOX = Path("data") / "_demo_update"
TARGET = SANDBOX / "Phu_luc_demo.pdf"

DOCS = """
MATCH (:KnowledgeBase {kb_id: $kb})-[:HAS_DOCUMENT]->(d:Document)
OPTIONAL MATCH (d)-[:NEW_VERSION_OF]->(old:Document)
RETURN d.doc_id AS doc_id, d.version AS version, d.is_current AS is_current,
       d.content_hash AS hash, d.superseded_reason AS reason,
       old.doc_id AS new_version_of, COUNT { (d)-[:HAS_CHUNK]->() } AS chunks
ORDER BY d.version
"""

# Same filters as GRAPH_CANDIDATES in 05_retrieval.cypher, restricted to the sandbox.
RETRIEVE = """
MATCH (e:Entity {name: 'Vốn điều lệ'})<-[:MENTIONS]-(c:Chunk)<-[:HAS_CHUNK]-(d:Document)
MATCH (:KnowledgeBase {kb_id: $kb})-[:HAS_DOCUMENT]->(d)
WHERE coalesce(d.is_current, true) AND d.duplicate_of IS NULL
RETURN DISTINCT d.doc_id AS doc_id, d.version AS version, count(c) AS chunks
"""

RUNS = """
MATCH (r:IngestRun)-[:UPDATED]->(:KnowledgeBase {kb_id: $kb})
RETURN r.run_id AS run_id, r.inserted AS inserted, r.skipped AS skipped,
       r.new_version AS new_version, r.retired AS retired, r.failed AS failed
ORDER BY r.finished_at
"""


def step(store, name, result=None):
    docs = store._run(DOCS, kb=KB_DEMO)
    actions = [item.get("action") for item in (result or {}).get("loaded", [])]
    print(f"\n== {name}: actions={actions} retired={len((result or {}).get('retired', []))}")
    for doc in docs:
        print(f"   v{doc['version']} {doc['doc_id']} current={doc['is_current']} "
              f"chunks={doc['chunks']} new_version_of={doc['new_version_of']} reason={doc['reason']}")
    return {"step": name, "actions": actions, "documents": docs}


def cleanup(store) -> None:
    ids = [row["doc_id"] for row in store._run(DOCS, kb=KB_DEMO)]
    for doc_id in ids:
        store.delete_document(doc_id)
    store._run("MATCH (r:IngestRun)-[:UPDATED]->(:KnowledgeBase {kb_id: $kb}) DETACH DELETE r", kb=KB_DEMO)
    store._run("MATCH (k:KnowledgeBase {kb_id: $kb}) DETACH DELETE k", kb=KB_DEMO)
    shutil.rmtree(SANDBOX, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true", help="leave KB_DEMO in Neo4j for Browser screenshots")
    parser.add_argument("--out", default="debug/kb_update_demo.json")
    args = parser.parse_args()

    store = get_store()
    cleanup(store)
    SANDBOX.mkdir(parents=True, exist_ok=True)
    log = []
    try:
        shutil.copyfile(V1, TARGET)
        log.append(step(store, "1. nap lan dau", load_pdf_folder(store, SANDBOX, KB_DEMO, update=True, prune=True)))

        log.append(step(store, "2. nap lai, khong doi", load_pdf_folder(store, SANDBOX, KB_DEMO, update=True, prune=True)))

        shutil.copyfile(V2, TARGET)
        log.append(step(store, "3. noi dung thay doi", load_pdf_folder(store, SANDBOX, KB_DEMO, update=True, prune=True)))

        hits = store._run(RETRIEVE, kb=KB_DEMO)
        print(f"\n== 4. truy xuat 'Vốn điều lệ' tren KB_DEMO: {hits}")
        log.append({"step": "4. truy xuat", "hits": hits})

        TARGET.unlink()
        log.append(step(store, "5. nguon bi xoa", load_pdf_folder(store, SANDBOX, KB_DEMO, update=True, prune=True)))

        runs = store._run(RUNS, kb=KB_DEMO)
        print("\n== IngestRun")
        for run in runs:
            print("  ", run)
        log.append({"step": "nhat ky", "runs": runs})
    finally:
        if not args.keep:
            cleanup(store)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(log, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
