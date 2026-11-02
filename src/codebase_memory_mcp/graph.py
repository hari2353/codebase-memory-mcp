"""Git-nexus graph (T02): nodes = author/commit/file/symbol, edges =
authored/modified/contains, stdlib sqlite. Read APIs back the MCP tools."""
from __future__ import annotations

import json
import functools
import sqlite3
import threading

_SCHEMA = """
CREATE TABLE nodes (
  repo TEXT, kind TEXT, name TEXT, path TEXT DEFAULT '', occurred_at TEXT DEFAULT '',
  meta TEXT DEFAULT '{}', key TEXT PRIMARY KEY
);
CREATE TABLE edges (
  repo TEXT, relation TEXT, src TEXT, dst TEXT, occurred_at TEXT DEFAULT ''
);
CREATE INDEX edges_dst_rel ON edges(dst, relation);
CREATE INDEX edges_src_rel ON edges(src, relation);
"""

def locked(fn):
    """Serialize DB access: MCP v2 runs tool bodies in worker threads."""
    @functools.wraps(fn)
    def wrapper(self, *a, **kw):
        with self._lock:
            return fn(self, *a, **kw)
    return wrapper


class GitNexusGraph:
    def __init__(self, path: str = ":memory:"):
        # MCP v2 runs tool bodies in worker threads; keep one shared conn + lock
        self.db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self.db.row_factory = sqlite3.Row
        self.db.executescript(_SCHEMA)

    # ---------- write ----------
    @locked
    def load(self, index: dict) -> None:
        repo = index["repo"]
        for t in index["tree"]:
            key = f"file|{repo}|{t['path']}"
            self.db.execute(
                "INSERT OR REPLACE INTO nodes VALUES (?,?,?,?,?,?,?)",
                (repo, "file", t["path"], t["path"], "", json.dumps({"size": t["size"], "lang": t["lang"]}), key))
            for s in t.get("symbols", []):
                skey = f"symbol|{repo}|{t['path']}|{s['name']}"
                self.db.execute(
                    "INSERT OR REPLACE INTO nodes VALUES (?,?,?,?,?,?,?)",
                    (repo, "symbol", s["name"], t["path"], "", s["kind"], skey))
                self.db.execute("INSERT OR REPLACE INTO edges VALUES (?,?,?,?,?)",
                                (repo, "contains", key, skey, ""))
        for c in index["commits"]:
            ckey = f"commit|{repo}|{c['sha'][:12]}"
            akey = f"author|{repo}|{c['author_email']}"
            self.db.execute(
                "INSERT OR REPLACE INTO nodes VALUES (?,?,?,?,?,?,?)",
                (repo, "commit", c["subject"], "", c["occurred_at"],
                 json.dumps({"author_name": c["author_name"], "author_email": c["author_email"]}), ckey))
            self.db.execute(
                "INSERT OR REPLACE INTO nodes VALUES (?,?,?,?,?,?,?)",
                (repo, "author", c["author_name"], "", "", "{}", akey))
            self.db.execute("INSERT OR REPLACE INTO edges VALUES (?,?,?,?,?)",
                            (repo, "authored", akey, ckey, c["occurred_at"]))
            for path in [p for p in c["files_changed"].split("\n") if p]:
                self.db.execute("INSERT OR REPLACE INTO edges VALUES (?,?,?,?,?)",
                                (repo, "modified", ckey, f"file|{repo}|{path}", c["occurred_at"]))
        self.db.commit()

    # ---------- read ----------
    @locked
    def counts(self) -> list[tuple[str, int]]:
        pairs = []
        for res, label in ((self.db.execute(
                "SELECT kind, COUNT(*) FROM nodes GROUP BY kind"), "node"),
                (self.db.execute(
                    "SELECT relation, COUNT(*) FROM edges GROUP BY relation"), "edge")):
            for k, n in res.fetchall():
                pairs.append((k, n))
        return sorted(pairs)

    @locked
    def explain_file(self, repo: str, path: str) -> dict:
        frow = self.db.execute(
            "SELECT key, name FROM nodes WHERE kind='file' AND name=?", (path,)).fetchone()
        if not frow:
            return {"path": path, "symbols": [], "commits": []}
        symrows = self.db.execute(
            "SELECT name, meta AS kind, path FROM nodes WHERE kind='symbol' AND path=?",
            (path,)).fetchall()
        commits = [dict(r) for r in self.db.execute(
            """SELECT n.name AS subject, n.meta, e.occurred_at
               FROM edges e JOIN nodes n ON n.key = e.src
               WHERE e.relation='modified' AND e.dst = ? ORDER BY e.occurred_at DESC""",
            (frow["key"],))]
        commits = [{**c, **json.loads(c.pop("meta"))} for c in commits]
        return {"path": path, "symbols": [dict(r) for r in symrows], "commits": commits}

    @locked
    def team_activity(self, repo: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT n.name AS author_name, COUNT(*) AS commits FROM edges e "
            "JOIN nodes n ON n.key = e.src WHERE e.relation='authored' GROUP BY e.src")
        return [dict(r) for r in rows]

    @locked
    def get_codebase_context(self, repo: str, query: str, top_k: int = 5) -> dict:
        words = query.lower().split()
        tokens: dict[str, set[str]] = {}
        for r in self.db.execute(
                "SELECT name, path, meta AS kind FROM nodes WHERE kind='symbol'"):
            tokens.setdefault(r["path"], set()).add(r["name"].lower())

        def hits(word: str, tok: str) -> bool:
            return word in tok or tok in word

        scored = []
        for r in self.db.execute("SELECT name, meta FROM nodes WHERE kind='file'"):
            toks = tokens.get(r["name"], set()) | {r["name"].lower()}
            score = sum(1 for w in words for t in toks if hits(w, t))
            scored.append((score, r))
        top = [{"path": r["name"], "rank": s}
               for s, r in sorted(scored, key=lambda x: -x[0])[:top_k] if s > 0]
        recent = [dict(r) for r in self.db.execute(
            "SELECT n.name AS subject, e.occurred_at FROM edges e JOIN nodes n ON n.key = e.dst "
            "WHERE e.relation='authored' ORDER BY e.occurred_at DESC LIMIT ?", (top_k,))]
        return {"repo": repo, "top_files": top, "recent_commits": recent}

    @locked
    def search_codebase_memory(self, repo: str, text: str) -> list[dict]:
        rows = self.db.execute(
            "SELECT name, path, meta AS kind FROM nodes "
            "WHERE kind='symbol' AND name LIKE ? LIMIT 20", (f"%{text}%",))
        return [dict(r) for r in rows]

    @locked
    def detect_changes(self, repo: str, changed_files: list[str]) -> dict:
        """Map a set of changed files to their symbols + recent commits (blast radius)."""
        out_files = []
        for path in changed_files:
            frow = self.db.execute(
                "SELECT key, name FROM nodes WHERE kind='file' AND name=?", (path,)).fetchone()
            if not frow:
                out_files.append({"path": path, "symbols": [], "recent_commits": []})
                continue
            syms = [dict(r) for r in self.db.execute(
                "SELECT name, meta AS kind FROM nodes WHERE kind='symbol' AND path=?",
                (path,))]
            commits = [dict(r) for r in self.db.execute(
                "SELECT n.name AS subject, e.occurred_at FROM edges e "
                "JOIN nodes n ON n.key=e.src WHERE e.relation='modified' AND e.dst=? "
                "ORDER BY e.occurred_at DESC LIMIT 5", (frow["key"],))]
            out_files.append({"path": path, "symbols": syms, "recent_commits": commits})
        return {"repo": repo, "changed": out_files,
                "total_symbols": sum(len(f["symbols"]) for f in out_files)}

