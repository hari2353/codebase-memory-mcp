# Spec: codebase-memory-mcp — MCP Server for Codebase Memory

## Objective
MCP (Model Context Protocol) server that provides persistent memory and
context for AI coding agents. Stores and retrieves codebase knowledge,
decisions, and context across sessions.

## IG-Mined Topics (cross-pollination)
- MCP (T07-04): MCP deep dive, tool engineering, agent protocols
- Agent Memory (T07-10): working, episodic, semantic, procedural memory
- Context Engineering (T07-11): budgets, compaction, context editing, subagents
- Tool Engineering (T07-03): schemas, errors, idempotency, sandboxing
- Harness Engineering (T07-25): 15-component model, everything except the model
- RAG (T06): retrieval for code context, semantic search
- Embeddings (T06-02): code embeddings, vector search

## Tech Stack
- Python, MCP SDK, pyproject.toml, pytest
- Storage: local (SQLite/vector), no cloud dependencies

## Commands
```bash
pytest tests/ -q
```
