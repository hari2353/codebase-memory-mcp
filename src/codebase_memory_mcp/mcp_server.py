"""MCP server (T01): FastMCP tools backed by the in-process GitNexusGraph.
Run:  python -m codebase_memory_mcp.mcp_server            # stdio
"""
from __future__ import annotations

from .graph import GitNexusGraph

_GRAPH: GitNexusGraph | None = None


def set_graph(graph: GitNexusGraph) -> None:
    global _GRAPH
    _GRAPH = graph


def get_graph() -> GitNexusGraph:
    if _GRAPH is None:
        raise RuntimeError("no graph loaded; run index_repository(repo_path) first or call set_graph()")
    return _GRAPH


def index_repository(repo_path: str) -> dict:
    from .repoindex import index_repo
    data = index_repo(repo_path)
    graph = get_graph() if _GRAPH is not None else GitNexusGraph()
    graph.load(data)
    set_graph(graph)
    return {"indexed": repo_path, "commits": len(data["commits"]),
            "files": len(data["tree"]), "symbols": len(data["symbols"])}


# ---- tool bodies (tested directly; FastMCP wraps them below) ----

def get_codebase_context(ctx=None, repo: str = "*", query: str = "") -> dict:
    return get_graph().get_codebase_context(repo, query)


def search_codebase_memory(ctx=None, repo: str = "*", query: str = "") -> list[dict]:
    return get_graph().search_codebase_memory(repo, query)


def explain_file(ctx=None, repo: str = "*", path: str = "") -> dict:
    return get_graph().explain_file(repo, path)


def team_activity(ctx=None, repo: str = "*") -> list[dict]:
    return get_graph().team_activity(repo)


def build_mcp():
    """MCP app with the 4 tools (stdio, matches GMP's ≤4-tool rule)."""
    try:
        from mcp.server.mcpserver import MCPServer          # mcp 2.x
    except ImportError:
        from mcp.server.fastmcp import FastMCP as MCPServer  # mcp 1.x
    mcp = MCPServer("codebase-memory")

    @mcp.tool()
    def get_codebase_context(repo: str, query: str) -> dict:
        """Relevant files + recent commits for a work query, from repo memory."""
        return get_graph().get_codebase_context(repo, query)

    @mcp.tool()
    def search_codebase_memory(repo: str, query: str) -> list[dict]:
        """Search indexed symbols (functions/classes) by name fragment."""
        return get_graph().search_codebase_memory(repo, query)

    @mcp.tool()
    def explain_file(repo: str, path: str) -> dict:
        """Provenance for one file: its symbols + commits that modified it."""
        return get_graph().explain_file(repo, path)

    @mcp.tool()
    def team_activity(repo: str) -> list[dict]:
        """Commits per author in the indexed repo(s)."""
        return get_graph().team_activity(repo)

    @mcp.resource("codebase://indexed")
    def indexed() -> str:
        from .graph import _SCHEMA
        return "codebase-memory MCP; sources indexed via index_repository tool."

    return mcp


def main(repo_path: str | None = None) -> None:
    if repo_path is None:  # console script (uvx) calls main() with no args
        import sys
        repo_path = sys.argv[1] if len(sys.argv) > 1 else None
    if repo_path:
        from .repoindex import index_repo
        g = GitNexusGraph()
        g.load(index_repo(repo_path))
        set_graph(g)
    build_mcp().run()  # stdio transport


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else None)
