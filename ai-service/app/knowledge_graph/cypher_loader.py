"""Load named Cypher queries from the .cypher files in ./cypher.

Each query starts with a marker line `// :name QUERY_NAME` and runs until the
next marker. Statements end with `;` so the same files also run unchanged in
cypher-shell or Neo4j Browser.
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

CYPHER_DIR = Path(__file__).resolve().parent / "cypher"
_MARKER = re.compile(r"^//\s*:name\s+([A-Z][A-Z0-9_]*)\s*$", re.MULTILINE)
_STATEMENT_END = re.compile(r";\s*$", re.MULTILINE)


def _strip_comments(block: str) -> str:
    lines = [line for line in block.splitlines() if not line.lstrip().startswith("//")]
    return "\n".join(lines).strip()


def parse(text: str) -> Dict[str, str]:
    """Map query name -> Cypher text (comments and trailing `;` removed)."""
    queries: Dict[str, str] = {}
    markers = list(_MARKER.finditer(text))
    for index, marker in enumerate(markers):
        end = markers[index + 1].start() if index + 1 < len(markers) else len(text)
        body = _strip_comments(text[marker.end():end])
        name = marker.group(1)
        if name in queries:
            raise ValueError(f"Duplicate Cypher query name: {name}")
        queries[name] = body.rstrip().rstrip(";").rstrip()
    return queries


def split_statements(block: str) -> List[str]:
    """Split a block holding several `;`-terminated statements."""
    return [part.strip() for part in _STATEMENT_END.split(block) if part.strip()]


@lru_cache(maxsize=1)
def load_queries(directory: str = str(CYPHER_DIR)) -> Dict[str, str]:
    queries: Dict[str, str] = {}
    for path in sorted(Path(directory).glob("*.cypher")):
        for name, query in parse(path.read_text(encoding="utf-8")).items():
            if name in queries:
                raise ValueError(f"Cypher query {name} defined twice ({path.name})")
            queries[name] = query
    return queries
