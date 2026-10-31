# codebase-memory-mcp

MCP server that turns any local git repo into **codebase memory**: commits,
files, and symbols projected into a tiny graph (sqlite), exposed as exactly 4
MCP tools, and (optionally) emitted as
[graph-memory-platform](https://github.com/hari2353/graph-memory-platform)
cloudsignals (`codebase.<name>.v1`, CloudEvents 1.0).

Part of the T01/T02 milestone (docs ledger 2026-10-31).

## Tools

| Tool | What it answers |
|---|---|
| `get_codebase_context(repo, query)` | relevant files (symbol/name match) + recent commits |
| `search_codebase_memory(repo, query)` | indexed symbols by name fragment |
| `explain_file(repo, path)` | file provenance: symbols + commits that modified it |
| `team_activity(repo)` | commits per author |

`repo = "*"` scopes across every indexed repo in the same server.

## Usage

```bash
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"

# serve one repo (stdio MCP)
.venv/bin/python -m codebase_memory_mcp.mcp_server /path/to/repo

# wire-level proof: spawns the server, calls all 4 tools over stdio
.venv/bin/python scripts/e2e_client.py /path/to/repo
```

Unit tests: `.venv/bin/python -m pytest -q` (fixture git repos, 12 tests).

## Signals (graph-memory-platform integration)

`codebase_memory_mcp.signals.to_signals(index, sink)` emits CloudEvents
(`specversion`, `id`, `source`, `type`, `time`, `partitionkey`) shaped for
`POST /v1/signals:batch`. Sinks: `InMemorySink` (tests) and `GmpHttpSink`
(real platform). Signal types: `codebase.commit.v1`, `codebase.file_changed.v1`,
`codebase.symbol_seen.v1`.

## Design notes

- Symbol scan is regex (py/ts/md), deliberately no tree-sitter: file-level
  memory cheaply, upgrade path documented in the ledger.
- venv, crawl/session state, and anything secret never enter the repo.
