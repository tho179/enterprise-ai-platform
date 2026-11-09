"""Re-chunk and re-embed every uploaded document through the backend pipeline.

Use after changing the chunker or the embedding model. Runs from the host:
    python ai-service/scripts/14_reindex_uploads.py --email admin@congty.vn --password ...
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def call(base: str, method: str, path: str, token: str = "", body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(base + path, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def wait(base: str, token: str, task_id: str, timeout_s: int) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status = call(base, "GET", f"/api/ai/status/{task_id}", token)
        if status["status"] != "PROCESSING":
            return status
        time.sleep(3)
    return {"status": "TIMEOUT", "chunkCount": 0, "message": "still processing"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="http://localhost:8080")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--timeout", type=int, default=1800, help="seconds per document")
    args = parser.parse_args()

    login = call(args.base, "POST", "/api/auth/login", body={"email": args.email, "password": args.password})
    token = login.get("token") or login.get("accessToken")
    documents = call(args.base, "GET", "/api/documents", token)["items"]

    failed = 0
    for document in documents:
        version = document["currentVersion"]
        if version["status"] != "INGESTED":
            print(f"SKIP {document['documentCode']}: status {version['status']}", flush=True)
            continue
        started = time.time()
        try:
            ticket = call(args.base, "POST", f"/api/documents/versions/{version['id']}/reindex", token)
        except urllib.error.HTTPError as exc:
            failed += 1
            print(f"FAIL {document['documentCode']}: HTTP {exc.code} {exc.read()[:200]!r}", flush=True)
            continue
        result = wait(args.base, token, ticket["taskId"], args.timeout)
        ok = result["status"] == "INGESTED"
        failed += 0 if ok else 1
        print(
            f"{'OK  ' if ok else 'FAIL'} {document['documentCode']}: "
            f"{version.get('chunkCount')} -> {result.get('chunkCount')} chunks "
            f"in {time.time() - started:.0f}s {'' if ok else result.get('message')}",
            flush=True,
        )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
