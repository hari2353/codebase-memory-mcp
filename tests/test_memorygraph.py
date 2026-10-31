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



def test_retain_recall_reflect_and_observe():
    g = MemoryGraph()
    g.add_entity("p", "proj", "project")
    g.retain("p", "shipped v1", "2026-10-31T09:00:00Z")
    g.retain("p", "fixed parser bug", "2026-10-31T10:00:00Z")
    g.observe("p", "parser bug was stream-layout issue")
    r = g.recall("p", query="parser")
    assert len(r["episodes"]) == 1 and "parser" in r["episodes"][0]["text"]
    rf = g.reflect("p")
    assert "parser bug was stream-layout issue" in rf["mental_model"]
    assert len(rf["episodes"]) == 2  # most recent 2... actually limit 5
    g.close()


def test_recall_time_window():
    g = MemoryGraph()
    g.add_entity("p", "proj", "project")
    g.retain("p", "early", "2026-10-01T00:00:00Z")
    g.retain("p", "late", "2026-10-31T00:00:00Z")
    r = g.recall("p", since="2026-10-15T00:00:00Z")
    assert [e["text"] for e in r["episodes"]] == ["late"]
    g.close()

