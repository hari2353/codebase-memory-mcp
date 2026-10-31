from codebase_memory_mcp.repoindex import index_repo
from codebase_memory_mcp.graph import GitNexusGraph


def test_mcp_tool_wrappers_call_graph(sample_repo):
    import importlib
    g = GitNexusGraph(":memory:")
    g.load(index_repo(sample_repo))
    from codebase_memory_mcp import mcp_server
    mcp_server.set_graph(g)
    ctx = mcp_server.get_codebase_context(ctx=None, repo=str(sample_repo), query="greeting")
    assert ctx["repo"] == str(sample_repo)
    assert mcp_server.search_codebase_memory(ctx=None, repo="*", query="Greeter")
    assert mcp_server.explain_file(ctx=None, repo="*", path="app.py")["path"] == "app.py"
    assert mcp_server.team_activity(ctx=None, repo="*")
