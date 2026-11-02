from codebase_memory_mcp.repoindex import index_repo
from codebase_memory_mcp.graph import GitNexusGraph


def test_detect_changes_returns_symbols_and_commits(sample_repo):
    g = GitNexusGraph(":memory:")
    g.load(index_repo(sample_repo))
    out = g.detect_changes("*", ["app.py", "nope.py"])
    assert out["total_symbols"] >= 2  # greet + Greeter
    changed = {f["path"]: f for f in out["changed"]}
    assert "greet" in {s["name"] for s in changed["app.py"]["symbols"]}
    assert changed["nope.py"]["symbols"] == []
    assert changed["app.py"]["recent_commits"]  # at least one commit touched it
