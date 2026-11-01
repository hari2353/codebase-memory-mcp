from pathlib import Path
from codebase_memory_mcp.repoindex import index_repo
from codebase_memory_mcp.graph import GitNexusGraph
from codebase_memory_mcp.wiring import inject_context


def test_inject_context_returns_files_and_commits(sample_repo):
    g = GitNexusGraph(":memory:")
    g.load(index_repo(sample_repo))
    out = inject_context(g, "*", "greeting")
    assert "Relevant files:" in out
    assert "app.py" in out or "util.ts" in out
    assert "Recent commits:" in out

