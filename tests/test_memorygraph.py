from codebase_memory_mcp.memorygraph import MemoryGraph


def test_entity_and_episode_roundtrip():
    g = MemoryGraph()
    g.add_entity("proj:cm", "codebase-memory-mcp", "project", {"lang": "py"})
    g.add_episode("proj:cm", "indexed stair-vs-rag", "2026-10-31T09:00:00Z", "indexer")
    ctx = g.context_for("proj:cm")
    assert ctx["name"] == "codebase-memory-mcp"
    assert ctx["meta"] == {"lang": "py"}
    assert len(ctx["episodes"]) == 1
    assert ctx["episodes"][0]["text"] == "indexed stair-vs-rag"
    g.close()


def test_context_missing_entity_returns_none():
    assert MemoryGraph().context_for("nope") is None


def test_search_finds_by_name_and_meta():
    g = MemoryGraph()
    g.add_entity("p1", "alpha", "project", {"tag": "trading"})
    g.add_entity("p2", "beta", "project", {"tag": "jobhunt"})
    assert {e["key"] for e in g.search("trading")} == {"p1"}
    assert {e["key"] for e in g.search("beta")} == {"p2"}
    g.close()

