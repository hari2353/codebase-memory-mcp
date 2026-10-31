"""Workflow-event adapter (T04): turn session/tool activity into GMP-shaped
CloudEvents so an agent's own actions become part of the memory graph.

Events are deliberately tiny: tool name, repo, user, outcome, occurred_at.
Sink reuse: `InMemorySink` / `GmpHttpSink` from `signals`.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from .signals import InMemorySink, signal_type

WORKFLOW_TYPE = signal_type("workflow")  # codebase.workflow.v1


def make_event(tool: str, repo: str = "*", user: str = "agent",
               outcome: str = "ok", occurred_at: str | None = None) -> dict:
    return {
        "tool": tool, "repo": repo, "user": user, "outcome": outcome,
        "occurred_at": occurred_at or datetime.now(timezone.utc).isoformat(),
        "id": str(uuid.uuid4()),
    }


class WorkflowRecorder:
    """Append-only in-process recorder; flush() pushes to a sink and clears."""

    def __init__(self):
        self.events: list[dict] = []

    def record(self, tool: str, **kw) -> dict:
        ev = make_event(tool, **kw)
        self.events.append(ev)
        return ev

    def flush(self, sink) -> int:
        envs = [to_envelope(e) for e in self.events]
        n = sink.push(envs)
        self.events.clear()
        return n


def to_envelope(ev: dict) -> dict:
    return {
        "specversion": "1.0",
        "id": ev["id"],
        "source": f"workflow://{ev['repo']}",
        "type": WORKFLOW_TYPE,
        "time": ev["occurred_at"],
        "partitionkey": ev["user"],
        "data": {"tool": ev["tool"], "repo": ev["repo"], "outcome": ev["outcome"]},
    }


def to_workflow_signals(events: list[dict], sink) -> int:
    return sink.push([to_envelope(e) for e in events])

