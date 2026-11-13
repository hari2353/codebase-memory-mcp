---
name: codebase-memory-mcp
description: Turn any local git repo into persistent codebase memory for your coding agent - commits, files and symbols in a queryable graph served over MCP (stdio). Use this skill whenever the user asks to index a repo, give the agent codebase/project/repo memory, remember the codebase, find where something is implemented, find a symbol by name, see who wrote or last changed a file, review recent changes, list main contributors, or set up the codebase-memory-mcp MCP server in Claude Code, Cursor, Copilot or any other MCP client - even if they don't name the server.
---

# Codebase Memory (MCP server)

codebase-memory-mcp turns a local git repo into **codebase memory**: commits,
files and symbols projected into a small SQLite graph, exposed as exactly 4
MCP tools over stdio. One tool call answers "where is X", "who wrote Y" or
"what changed recently" - instead of grepping and reading files one by one.

Repo: https://github.com/hari2353/codebase-memory-mcp (MIT)

## How the agent should use it

Once the `codebase-memory` MCP server is configured, prefer these tools over
repeated grep/read for structural questions; then read only the returned
files for the actual code. The graph finds the code - it does not replace
reading it.

| Tool | Call when | Args | Returns |
|---|---|---|---|
| `get_codebase_context` | Default entry point for any work question ("where do I add X", "how does checkout work") | `repo="*"`, `query` (2-4 keywords) | `{"top_files": [{path, rank}], "recent_commits": [{subject, occurred_at}]}` |
| `search_codebase_memory` | Find symbols by name fragment ("where is the OrderProcessor class") | `repo="*"`, `query` (name fragment) | `[{name, path, kind}]` |
| `explain_file` | History/ownership of one file ("who's been changing this file") | `repo="*"`, `path` (repo-relative) | `{path, symbols, commits: [{subject, author_name, occurred_at}]}` |
| `team_activity` | Contributor overview | `repo="*"` | `[{author_name, commits}]` |

Notes:

- `repo` is a required argument; `"*"` matches whatever this server indexed
  and is always the right value (one server hosts one repo).
- The graph is a snapshot taken when the server started. After heavy
  changes, restart the MCP server (or reopen the project) to re-index.
- Symbols cover `.py` (def/class), `.ts` (function/class) and `.md`
  (top-level headings); the file tree covers every tracked file. There is no
  call graph - don't answer "who calls X" from these tools.
- `search_codebase_memory` does a `LIKE %fragment%` match, so shorter
  fragments match more.

## Setup (per project, run by the agent)

Zero-setup install via [uv](https://docs.astral.sh/uv/): no venv, no pip, no
absolute paths - `uvx` fetches, builds and caches the server from GitHub
automatically (it even manages Python itself). Prerequisite: `git` on PATH.

1. Make sure `uv` exists (skip if `uvx --version` works):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh   # Windows: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

2. Register the server. It indexes the repo passed as its only argument, so
   **each project needs its own entry** with the repo's absolute path.
   **Claude Code - one command:**

```bash
claude mcp add codebase-memory -- uvx --from git+https://github.com/hari2353/codebase-memory-mcp cbm-memory /absolute/path/to/the/repo
```

   Any other MCP client - copy `mcp-config.example.json` (next to this file):

```json
{
  "mcpServers": {
    "codebase-memory": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/hari2353/codebase-memory-mcp", "cbm-memory", "/absolute/path/to/the/repo"]
    }
  }
}
```

   (Cursor: paste into `~/.cursor/mcp.json`; Codex/Copilot CLI: same shape.)

3. Restart the agent (or reload MCP servers) so it picks up the config.

4. Verify: ask the agent what MCP tools it sees. You should see exactly 4:
   `get_codebase_context`, `search_codebase_memory`, `explain_file`,
   `team_activity`. Then ask it to answer a question about the repo (e.g.
   "where is the main entry point?") using `get_codebase_context`.

**Privacy: everything stays on your machine.** Indexing and the SQLite graph
run locally; repo code, the index and tool results are never uploaded
anywhere. (No `uv` or prefer explicit installs? Fallback: `python3 -m venv
~/.cbm-mcp-venv && ~/.cbm-mcp-venv/bin/pip install
"git+https://github.com/hari2353/codebase-memory-mcp.git"`, then point the
MCP client at `~/.cbm-mcp-venv/bin/python -m codebase_memory_mcp.mcp_server
<repo>`.)

## Troubleshooting

- Tools missing → server not configured or agent not restarted; recheck the
  config JSON and restart.
- Result contains "no graph loaded" → the server was started without the
  repo path argument; add it to `args`.
- Empty results → wrong repo path in `args`, or the repo has no commits yet.
- Server exits at startup → the repo path is not a git repo; the path must
  contain a `.git` directory.
