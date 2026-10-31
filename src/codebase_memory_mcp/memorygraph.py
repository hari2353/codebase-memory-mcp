"""LLM memory graph (T05): entity + episode store with context read-back.

Borrowed ideas:
- Hindsight (vectorize-io/hindsight): retain / recall / reflect triad, observations
  (consolidated facts), mental models, temporal validity.
- Hermes (nousresearch/hermes-agent): FTS5 full-text search over episodes instead
  of LIKE, agent-curated persistence (the caller decides what to retain).

Entities are durable things (person, project, concept); episodes are
time-stamped observations attached to an entity; observations are consolidated
facts derived from episodes. `context_for(key)` returns the entity plus its
recent episodes — the read-back an agent needs to stay consistent.
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
        CREATE VIRTUAL TABLE IF NOT EXISTS episodes_fts USING fts5(
            text, content='episodes', content_rowid='id');
        CREATE TRIGGER IF NOT EXISTS episodes_ai AFTER INSERT ON episodes BEGIN
            INSERT INTO episodes_fts(rowid, text) VALUES (new.id, new.text);
        END;
        CREATE TRIGGER IF NOT EXISTS episodes_ad AFTER DELETE ON episodes BEGIN
            INSERT INTO episodes_fts(episodes_fts, rowid, text) VALUES('delete', old.id, old.text);
        END;
        """)

    def add_entity(self, key: str, name: str, kind: str = "concept", meta=None) -> None:
        with self._lock:
            self.db.execute(
                "INSERT OR REPLACE INTO entities VALUES (?,?,?,?)",
                (key, name, kind, json.dumps(meta or {})))
            self.db.commit()

    def retain(self, entity_key: str, text: str, occurred_at: str, source: str = "") -> int:
        """Alias for add_episode: the hindsight 'retain' verb."""
        return self.add_episode(entity_key, text, occurred_at, source)

    def add_episode(self, entity_key: str, text: str, occurred_at: str,
                    source: str = "") -> int:
        with self._lock:
            cur = self.db.execute(
                "INSERT INTO episodes (entity_key, text, occurred_at, source) VALUES (?,?,?,?)",
                (entity_key, text, occurred_at, source))
            self.db.commit()
            return cur.lastrowid

    def observe(self, entity_key: str, fact: str) -> None:
        """Consolidate a durable fact into the entity's mental model (observations)."""
        ent = self.get_entity(entity_key)
        if ent is None:
            return
        meta = ent["meta"]
        obs = meta.setdefault("observations", [])
        if fact not in obs:
            obs.append(fact)
        with self._lock:
            self.db.execute("UPDATE entities SET meta=? WHERE key=?",
                            (json.dumps(meta), entity_key))
            self.db.commit()

    def get_entity(self, key: str) -> dict | None:
        with self._lock:
            row = self.db.execute(
                "SELECT key, name, kind, meta FROM entities WHERE key=?", (key,)).fetchone()
            if not row:
                return None
            return {"key": row["key"], "name": row["name"], "kind": row["kind"],
                    "meta": json.loads(row["meta"])}

    def recall(self, key: str, query: str | None = None, since: str | None = None,
               until: str | None = None, limit: int = 20) -> dict | None:
        """Read-back with optional full-text filter and time window."""
        ent = self.get_entity(key)
        if ent is None:
            return None
        with self._lock:
            if query:
                rows = self.db.execute(
                    "SELECT e.text, e.occurred_at, e.source FROM episodes e "
                    "JOIN episodes_fts f ON f.rowid = e.id "
                    "WHERE e.entity_key=? AND episodes_fts MATCH ? "
                    "AND (? IS NULL OR e.occurred_at >= ?) "
                    "AND (? IS NULL OR e.occurred_at <= ?) "
                    "ORDER BY e.occurred_at DESC LIMIT ?",
                    (key, query, since, since, until, until, limit)).fetchall()
            else:
                rows = self.db.execute(
                    "SELECT text, occurred_at, source FROM episodes "
                    "WHERE entity_key=? "
                    "AND (? IS NULL OR occurred_at >= ?) "
                    "AND (? IS NULL OR occurred_at <= ?) "
                    "ORDER BY occurred_at DESC LIMIT ?",
                    (key, since, since, until, until, limit)).fetchall()
        ent["episodes"] = [dict(r) for r in rows]
        return ent

    def context_for(self, key: str, limit: int = 20) -> dict | None:
        """Back-compat read-back (no filter)."""
        return self.recall(key, limit=limit)

    def reflect(self, key: str) -> dict | None:
        """Mental model: entity + observations + most recent episodes."""
        ent = self.recall(key, limit=5)
        if ent is None:
            return None
        ent["mental_model"] = ent["meta"].get("observations", [])
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

