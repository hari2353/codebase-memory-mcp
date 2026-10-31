"""E2E proof: spawn the real MCP server over stdio and drive all 4 tools.

Usage: .venv/bin/python scripts/e2e_client.py /path/to/some/repo
"""
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

REPO_ROOT = Path(__file__).resolve().parents[1]


def payload(result):
    sc = getattr(result, "structured_content", None)
    if sc is None:  # mcp 1.x alias
        sc = getattr(result, "structuredContent", None)
    if isinstance(sc, dict) and "result" in sc:
        return sc["result"]
    if sc is not None:
        return sc
    return json.loads(result.content[0].text)


async def main(repo: str) -> None:
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "codebase_memory_mcp.mcp_server", repo],
        cwd=str(REPO_ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            tools = [t.name for t in (await s.list_tools()).tools]
            print("TOOLS:", tools)
            assert set(tools) == {"get_codebase_context", "search_codebase_memory",
                                  "explain_file", "team_activity"}, tools

            r = payload(await s.call_tool("get_codebase_context",
                                          {"repo": repo, "query": "symbol benchmark"}))
            print("CTX top_files:", [f["path"] for f in r["top_files"]])
            assert r["top_files"] and r["recent_commits"]

            r = payload(await s.call_tool("search_codebase_memory",
                                          {"repo": repo, "query": "test"}))
            print(f"SEARCH hits: {len(r)}", [h["name"] for h in r][:5])
            assert isinstance(r, list)

            target = next((h["path"] for h in r if h.get("path", "").endswith(".py")), None)
            if target is None:  # fallback: pick any indexed py file via CTX
                target = next(f["path"] for f in payload(await s.call_tool(
                    "get_codebase_context", {"repo": repo, "query": "0"}))["top_files"])
            r = payload(await s.call_tool("explain_file", {"repo": repo, "path": target}))
            print("EXPLAIN", target, "commits:", len(r["commits"]))
            assert r["commits"], "expected at least one commit touching the file"

            r = payload(await s.call_tool("team_activity", {"repo": repo}))
            print("TEAM:", r)
            assert r
    print("E2E OK: wire contract proven over stdio")


asyncio.run(main(sys.argv[1]))
