"""Signal adapter: emit GMP-shaped CloudEvents (graph-memory-platform SPEC §6,
`POST /v1/signals:batch` input). Types: `codebase.<name>.v1`; user_key =
author email; dedup identity = source (git://repo) + id (sha[:12]:path)."""
from __future__ import annotations

import re

SIGNAL_NS = "codebase"
SIGNAL_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,3}\.v[0-9]+$")


def signal_type(name: str) -> str:
    return f"{SIGNAL_NS}.{name}.v1"


class InMemorySink:
    def __init__(self):
        self.signals: list[dict] = []

    def push(self, envelopes: list[dict]) -> int:
        self.signals.extend(envelopes)
        return len(envelopes)


class GmpHttpSink:
    """Real GMP ingest: POST <base>/v1/signals:batch with the envelope list."""

    def __init__(self, base_url: str, token: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def push(self, envelopes: list[dict]) -> int:
        import requests  # lazy so unit tests don't need it

        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        r = requests.post(f"{self.base_url}/v1/signals:batch",
                          json=envelopes, headers=headers, timeout=10)
        r.raise_for_status()
        return r.json().get("accepted", len(envelopes)) if "json" in r.headers.get("content-type", "") else 1


def to_signals(index: dict, sink) -> int:
    repo = index["repo"]
    source = f"git://{repo}"
    envelopes: list[dict] = []
    for c in index["commits"]:
        envelopes.append({
            "specversion": "1.0",
            "id": f"{c['sha'][:12]}",
            "source": source,
            "type": signal_type("commit"),
            "time": c["occurred_at"],
            "partitionkey": c["author_email"] or c["author_name"] or "unknown",
            "data": {"sha": c["sha"], "author_name": c["author_name"],
                     "author_email": c["author_email"], "subject": c["subject"],
                     "files": c["files_changed"].split()},
        })
        for path in c["files_changed"].split():
            envelopes.append({
                "specversion": "1.0",
                "id": f"{c['sha'][:12]}:{path}",
                "source": source,
                "type": signal_type("file_changed"),
                "time": c["occurred_at"],
                "partitionkey": c["author_email"] or c["author_name"] or "unknown",
                "data": {"path": path, "sha": c["sha"]},
            })
    for s in index["symbols"]:
        envelopes.append({
            "specversion": "1.0",
            "id": f"sym:{s['path']}:{s['kind']}:{s['name']}",
            "source": source,
            "type": signal_type("symbol_seen"),
            "time": "2026-10-31T00:00:00Z",
            "partitionkey": "codebase",
            "data": {"path": s["path"], "kind": s["kind"], "name": s["name"]},
        })
    return sink.push([e for e in envelopes if SIGNAL_RE.match(e["type"])])
