"""End-to-end check against the running compose stack (run from the host).

Uploads a copy of an existing PDF restricted to MANAGER, then verifies:
- every chunk reaches Postgres, Qdrant and Neo4j under the same chunk_id;
- chat through the gateway returns a citation resolvable to that document;
- an EMPLOYEE can neither see the document nor receive answers from it;
- deleting the document removes it from every store.

    python ai-service/scripts/16_e2e_smoke.py --password <demo password>
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def env_file() -> dict:
    values = {}
    for line in (ROOT / ".env").read_text(encoding="utf8").splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def request(url, method="GET", body=None, headers=None, raw=False):
    data = json.dumps(body).encode() if isinstance(body, (dict, list)) else body
    req = urllib.request.Request(url, data=data, method=method)
    if isinstance(body, (dict, list)):
        req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    with urllib.request.urlopen(req, timeout=240) as response:
        payload = response.read()
    return payload if raw else json.loads(payload or b"{}")


def status_of(url, headers):
    try:
        request(url, headers=headers, raw=True)
        return 200
    except urllib.error.HTTPError as exc:
        return exc.code


def multipart(fields, file_bytes):
    boundary = uuid.uuid4().hex
    parts = []
    for key, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
        )
    parts.append(
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="e2e.pdf"\r\n'
            "Content-Type: application/pdf\r\n\r\n"
        ).encode()
        + file_bytes
        + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def check(label, condition, detail=""):
    print(f"{'PASS' if condition else 'FAIL'} {label} {detail if not condition else ''}", flush=True)
    return bool(condition)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:3000")
    parser.add_argument("--password", required=True)
    args = parser.parse_args()
    env = env_file()
    base = args.base

    def login(email):
        result = request(f"{base}/api/auth/login", "POST", {"email": email, "password": args.password})
        return {"Authorization": "Bearer " + (result.get("accessToken") or result.get("token"))}

    admin, manager, employee = login("admin@congty.vn"), login("manager@congty.vn"), login("nva@congty.vn")
    qdrant_headers = {"api-key": env["QDRANT_API_KEY"]}
    credentials = base64.b64encode(f"neo4j:{env['NEO4J_PASSWORD']}".encode()).decode()
    neo4j_headers = {"Authorization": f"Basic {credentials}"}

    documents = request(f"{base}/api/documents", headers=admin)["items"]
    source = min(documents, key=lambda item: item["currentVersion"]["chunkCount"])
    pdf = request(f"{base}/api/documents/{source['id']}/file", headers=admin, raw=True)

    code = f"E2E-{uuid.uuid4().hex[:8].upper()}"
    body, content_type = multipart(
        {"documentCode": code, "title": f"Kiểm thử {code}", "category": "Quy chế", "allowedRoles": "MANAGER"},
        pdf,
    )
    ticket = request(f"{base}/api/documents/upload", "POST", body, {**admin, "Content-Type": content_type})
    document_id = ticket["documentId"]

    results = []
    try:
        deadline = time.time() + 900
        while time.time() < deadline:
            task = request(f"{base}/api/ai/status/{ticket['taskId']}", headers=admin)
            if task["status"] != "PROCESSING":
                break
            time.sleep(3)
        results.append(check("upload ingested", task["status"] == "INGESTED", task))

        chunks = request(f"{base}/api/documents/{document_id}/chunks", headers=admin)
        chunk_ids = {chunk["chunkId"] for chunk in chunks}
        results.append(check("postgres has chunks", chunk_ids))

        def qdrant_ids():
            scroll = request(
                "http://localhost:6333/collections/enterprise_documents/points/scroll",
                "POST",
                {
                    "limit": 500,
                    "with_payload": True,
                    "filter": {"must": [{"key": "document_id", "match": {"value": document_id}}]},
                },
                qdrant_headers,
            )
            return {point["payload"]["chunk_id"] for point in scroll["result"]["points"]}

        def neo4j_ids():
            answer = request(
                "http://localhost:7474/db/neo4j/tx/commit",
                "POST",
                {
                    "statements": [{
                        "statement": "MATCH (d:Document {doc_id:$id})-[:HAS_CHUNK]->(c:Chunk) RETURN c.chunk_id",
                        "parameters": {"id": document_id},
                    }]
                },
                neo4j_headers,
            )
            return {row["row"][0] for row in answer["results"][0]["data"]}

        results.append(check("qdrant ids match postgres", qdrant_ids() == chunk_ids))
        results.append(check("neo4j ids match postgres", neo4j_ids() == chunk_ids))

        # A complete sentence from the document, so the gate has a real match.
        sentences = [
            " ".join(sentence.split())
            for chunk in chunks
            for sentence in re.split(r"(?<=[.;:])\s+", chunk["content"])
        ]
        question = max((s for s in sentences if s[:1].isupper() and len(s) <= 220), key=len)
        ask = {"query": question, "document_id": document_id, "top_k": 3}

        allowed = request(f"{base}/api/ai/chat", "POST", ask, manager)
        cited = {citation["chunk_id"] for citation in allowed["citations"]}
        results.append(check("manager gets a citation", cited and cited <= chunk_ids, allowed))

        denied = request(f"{base}/api/ai/chat", "POST", ask, employee)
        results.append(check("employee gets no citation", not denied["citations"], denied["citations"]))
        results.append(check(
            "employee cannot open the document",
            status_of(f"{base}/api/documents/{document_id}", employee) == 404,
        ))
        listed = {item["id"] for item in request(f"{base}/api/documents", headers=employee)["items"]}
        results.append(check("employee list hides the document", document_id not in listed))
        results.append(check(
            "manager can open the document",
            status_of(f"{base}/api/documents/{document_id}", manager) == 200,
        ))

        audit = request(f"{base}/api/ai/audit?limit=5", headers=admin)
        results.append(check("audit recorded the question", any(row["queryText"] == question for row in audit)))
        results.append(check("audit is admin only", status_of(f"{base}/api/ai/audit", manager) == 403))
    finally:
        request(f"{base}/api/documents", "DELETE", [document_id], admin)

    results.append(check("qdrant cleaned", not qdrant_ids()))
    results.append(check("neo4j cleaned", not neo4j_ids()))
    print(f"{sum(results)}/{len(results)} checks passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
