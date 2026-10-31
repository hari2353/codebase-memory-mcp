"""Obsidian vault ingestion (T09): read a local vault into the memory graph.

A vault is a directory of markdown notes plus a `.obsidian/` config dir.
We extract: note title (filename), body, [[wikilinks]], and #tags, and project
them as entities (notes, tags) + episodes (note body) + contains edges.
"""
from __future__ import annotations

import re
from pathlib import Path

WIKILINK = re.compile(r"\[\[([^\]\|#]+)(?:[^\]]*)\]\]")
TAG = re.compile(r"(?<!\w)#([A-Za-z][\w/-]*)")


def parse_note(path: Path, vault_root: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    rel = path.relative_to(vault_root).as_posix()
    title = path.stem
    links = sorted(set(WIKILINK.findall(text)))
    tags = sorted(set(TAG.findall(text)))
    return {"path": rel, "title": title, "text": text, "links": links, "tags": tags}


def scan_vault(vault_root: str | Path) -> list[dict]:
    root = Path(vault_root)
    if not root.is_dir():
        raise FileNotFoundError(str(root))
    notes = []
    for p in sorted(root.rglob("*.md")):
        if ".obsidian" in p.parts:
            continue
        notes.append(parse_note(p, root))
    return notes


def ingest_vault(vault_root, graph) -> int:
    """Project vault notes into a MemoryGraph. Returns number of notes ingested."""
    notes = scan_vault(vault_root)
    titles = {n["title"] for n in notes}
    for n in notes:
        graph.add_entity(f"note:{n['title']}", n["title"], "note",
                         {"path": n["path"], "tags": n["tags"]})
        graph.retain(f"note:{n['title']}", n["text"], "2026-01-01T00:00:00Z", "obsidian")
        for tag in n["tags"]:
            graph.add_entity(f"tag:{tag}", tag, "tag", {})
            graph.add_episode(f"tag:{tag}", f"tagged in {n['title']}",
                             "2026-01-01T00:00:00Z", "obsidian")
        for link in n["links"]:
            if link in titles:
                graph.add_entity(f"note:{link}", link, "note", {})
    return len(notes)

