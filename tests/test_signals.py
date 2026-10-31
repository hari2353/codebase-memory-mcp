import re

SIGNAL_TYPE_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,3}\.v[0-9]+$")


def test_signal_type_shape_matches_gmp_convention():
    from codebase_memory_mcp.signals import signal_type
    assert SIGNAL_TYPE_RE.match(signal_type("commit"))
    assert SIGNAL_TYPE_RE.match(signal_type("file_changed"))
    assert not SIGNAL_TYPE_RE.match("codebase.X.v1")   # uppercase segment: invalid
    assert not SIGNAL_TYPE_RE.match("codebase.commit")  # missing version: invalid


def test_committed_envelope_fields(sample_repo):
    from codebase_memory_mcp.signals import to_signals, InMemorySink
    from codebase_memory_mcp.repoindex import index_repo
    data = index_repo(sample_repo)
    sink = InMemorySink()
    to_signals(data, sink=sink)
    envs = sink.signals
    types = {e["type"] for e in envs}
    assert any(e["type"].endswith(".commit.v1") for e in envs)
    for e in envs:
        # CloudEvents 1.0 shape used by graph-memory-platform (SPEC §6)
        assert e["specversion"] == "1.0"
        assert e["source"].startswith("git://")
        assert e["partitionkey"]  # user_key: author email here
        assert isinstance(e["data"], dict)
        SIGNAL_TYPE_RE.match(e["type"])
    commit_env = [e for e in envs if e["type"].endswith(".commit.v1")][0]
    assert commit_env["data"]["author_email"] in {"h@x.dev", "n@x.dev"}
