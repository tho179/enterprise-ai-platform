"""Build the source inventory used by Chapter 4 (PDF files + public links)."""
from __future__ import annotations

import json
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[4]  # repo root
DOCS = ROOT / "ai-service" / "data" / "documents"
LINKS = ROOT / "ai-service" / "data" / "kb_sources" / "links.json"
OUT = Path(__file__).resolve().parent.parent / "assets"
OUT.mkdir(parents=True, exist_ok=True)


def main() -> None:
    rows = []
    for path in sorted(DOCS.rglob("*.pdf")):
        with pymupdf.open(path) as doc:
            pages = len(doc)
        rows.append(
            {
                "file": path.name,
                "relative_path": path.relative_to(DOCS).as_posix(),
                "category": path.parent.name,
                "pages": pages,
                "size_kb": round(path.stat().st_size / 1024, 1),
            }
        )

    links = json.loads(LINKS.read_text(encoding="utf-8"))["links"]
    summary = {
        "pdf_count": len(rows),
        "pdf_pages": sum(row["pages"] for row in rows),
        "categories": sorted({row["category"] for row in rows}),
        "link_count": len(links),
        "pdfs": rows,
        "links": links,
    }
    (OUT / "source_inventory.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "| # | Tệp PDF | Nhóm | Trang |",
        "| ---: | :--- | :--- | ---: |",
    ]
    for index, row in enumerate(rows, start=1):
        lines.append(f"| {index} | `{row['file']}` | {row['category']} | {row['pages']} |")
    (OUT / "pdf_inventory.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(rows)} PDF, {summary['pdf_pages']} pages, {len(links)} links")


if __name__ == "__main__":
    main()
