"""Use-case wiring (T12): turn codebase-memory context into a text block
that other repos (job-hunt-ai, bharat-arp, india-quant) can inject into
their prompts or evidence ledgers.
"""
from __future__ import annotations

from .graph import GitNexusGraph


def inject_context(graph: GitNexusGraph, repo: str, query: str, top_k: int = 5) -> str:
    """Return a compact, prompt-ready summary of relevant files + recent commits."""
    ctx = graph.get_codebase_context(repo, query, top_k=top_k)
    lines = [f"# Codebase context for: {query}", f"repo={repo}"]
    if ctx["top_files"]:
        lines.append("Relevant files:")
        for f in ctx["top_files"]:
            lines.append(f"  - {f['path']}")
    if ctx["recent_commits"]:
        lines.append("Recent commits:")
        for c in ctx["recent_commits"]:
            lines.append(f"  - {c.get('subject', '')} ({c.get('occurred_at', '')})")
    return "\n".join(lines)

