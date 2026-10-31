from codebase_memory_mcp.workflow import WorkflowRecorder, to_workflow_signals
from codebase_memory_mcp.signals import InMemorySink


def test_workflow_recorder_flushes_to_sink():
    rec = WorkflowRecorder()
    rec.record("search_codebase_memory", repo="*", user="agent", outcome="ok")
    rec.record("get_codebase_context", repo="*", user="agent", outcome="ok")
    sink = InMemorySink()
    n = rec.flush(sink)
    assert n == 2
    assert len(sink.signals) == 2
    assert all(e["type"] == "codebase.workflow.v1" for e in sink.signals)
    assert all(e["specversion"] == "1.0" for e in sink.signals)
    assert rec.events == []  # cleared after flush


def test_to_workflow_signals_direct():
    sink = InMemorySink()
    events = [{"tool": "x", "repo": "r", "user": "u", "outcome": "ok",
               "occurred_at": "2026-10-31T00:00:00Z", "id": "e1"}]
    assert to_workflow_signals(events, sink) == 1
    assert sink.signals[0]["partitionkey"] == "u"
    assert sink.signals[0]["data"]["tool"] == "x"

