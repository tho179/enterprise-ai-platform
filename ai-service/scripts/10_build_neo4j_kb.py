"""CLI: build the Neo4j knowledge base from PDFs and links, then merge KBs.

Examples:
  python scripts/10_build_neo4j_kb.py --init
  python scripts/10_build_neo4j_kb.py --pdf data/documents --kb KB1
  python scripts/10_build_neo4j_kb.py --links data/kb_sources/links.json --kb KB2
  python scripts/10_build_neo4j_kb.py --merge KB1 KB2 --target KB
  python scripts/10_build_neo4j_kb.py --export KB --out debug/kb_snapshot.json
  python scripts/10_build_neo4j_kb.py --pdf data/documents/quy_che_va_quy_trinh/Quy_che_hoat_dong_HDQT.pdf --dry-run --out debug/kb_sample.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.knowledge_graph.extract import build_pdf_record  # noqa: E402
from app.knowledge_graph.pipeline import (  # noqa: E402
    KB,
    KB1,
    KB2,
    load_links,
    load_pdf,
    load_pdf_folder,
    merge,
)
from app.knowledge_graph.store import Neo4jStore  # noqa: E402


def _links(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("links", [])
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--init", action="store_true", help="create constraints/indexes")
    parser.add_argument("--pdf", help="one PDF file or a folder")
    parser.add_argument("--links", help="JSON file with [{url,title}]")
    parser.add_argument("--kb", default=KB1, help="target KB for --pdf/--links")
    parser.add_argument("--merge", nargs="+", metavar="KB", help="source KB ids to merge")
    parser.add_argument("--target", default=KB)
    parser.add_argument("--export", metavar="KB")
    parser.add_argument("--out", default="debug/kb_snapshot.json")
    parser.add_argument("--update", action="store_true", help="hash-based incremental update")
    parser.add_argument("--dry-run", action="store_true", help="build JSON only, no Neo4j")
    args = parser.parse_args()

    if args.dry_run:
        if not args.pdf:
            parser.error("--dry-run requires --pdf")
        path = Path(args.pdf)
        records = []
        files = sorted(path.rglob("*.pdf")) if path.is_dir() else [path]
        for pdf in files:
            try:
                records.append(build_pdf_record(pdf))
            except Exception as exc:
                records.append({"path": str(pdf), "error": str(exc)})
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"wrote {out} ({len(records)} record(s))")
        return 0

    store = Neo4jStore(
        uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        user=os.getenv("NEO4J_USER", "neo4j"),
        password=os.getenv("NEO4J_PASSWORD", "eakwp-neo4j"),
        database=os.getenv("NEO4J_DATABASE", "neo4j"),
    )
    try:
        store.verify()
        if args.init:
            store.init_schema()
            print("schema ready")

        if args.pdf:
            path = Path(args.pdf)
            result = (
                load_pdf_folder(store, path, kb_id=args.kb, update=args.update)
                if path.is_dir()
                else load_pdf(store, path, kb_id=args.kb, update=args.update)
            )
            print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])

        if args.links:
            payload = _links(Path(args.links))
            result = load_links(
                store,
                [item["url"] for item in payload],
                kb_id=args.kb,
                update=args.update,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2)[:2000])

        if args.merge:
            print(json.dumps(merge(store, tuple(args.merge), target=args.target), ensure_ascii=False, indent=2))

        if args.export:
            data = store.sample(args.export, chunk_limit=8)
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"wrote {out}")
    finally:
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
