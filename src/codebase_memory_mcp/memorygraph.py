"""LLM memory graph (T05): entity + episode store with context read-back.

Entities are durable things (person, project, concept); episodes are time-stamped
observations attached to an entity. `context_for(key)` returns the entity plus
its recent episodes — the read-back an agent needs to stay consistent.
"""
from __future__ import annotations

import json
import sqlite3
import threading


class MemoryGraph:
    def __init__(self, path: str = ":memory:"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self._lock = threading.Lock()
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS entities (
            key TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL,
            meta TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, entity_key TEXT NOT NULL,
            text TEXT NOT NULL, occurred_at TEXT NOT NULL, source TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (entity_key) REFERENCES entities(key)
        );
        CREATE INDEX IF NOT EXISTS episodes_by_entity ON episodes(entity_key, occurred_at);
        """)

    def add_entity(self, key: str, name: str, kind: str = "concept", meta=None) -> None:
        with self._lock:
            self.db.execute(
                "INSERT OR REPLACE INTO entities VALUES (?,?,?,?)",
                (key, name, kind, json.dumps(meta or {})))
            self.db.commit()

    def add_episode(self, entity_key: str, text: str, occurred_at: str,
                    source: str = "") -> int:
        with self._lock:
            cur = self.db.execute(
                "INSERT INTO episodes (entity_key, text, occurred_at, source) VALUES (?,?,?,?)",
                (entity_key, text, occurred_at, source))
            self.db.commit()
            return cur.lastrowid

    def get_entity(self, key: str) -> dict | None:
        with self._lock:
            row = self.db.execute(
                "SELECT key, name, kind, meta FROM entities WHERE key=?", (key,)).fetchone()
            if not row:
                return None
            return {"key": row["key"], "name": row["name"], "kind": row["kind"],
                    "meta": json.loads(row["meta"])}

    def context_for(self, key: str, limit: int = 20) -> dict | None:
        ent = self.get_entity(key)
        if ent is None:
            return None
        with self._lock:
            rows = self.db.execute(
                "SELECT text, occurred_at, source FROM episodes "
                "WHERE entity_key=? ORDER BY occurred_at DESC LIMIT ?",
                (key, limit)).fetchall()
        ent["episodes"] = [dict(r) for r in rows]
        return ent

    def search(self, text: str, limit: int = 20) -> list[dict]:
        like = f"%{text}%"
        with self._lock:
            rows = self.db.execute(
                "SELECT key, name, kind, meta FROM entities "
                "WHERE name LIKE ? OR meta LIKE ? LIMIT ?",
                (like, like, limit)).fetchall()
        return [{"key": r["key"], "name": r["name"], "kind": r["kind"],
                 "meta": json.loads(r["meta"])} for r in rows]

    def close(self) -> None:
        self.db.close()

