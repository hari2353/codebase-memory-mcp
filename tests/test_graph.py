import pytest

from git_fixtures import sample_repo

from codebase_memory_mcp.repoindex import index_repo
from codebase_memory_mcp.graph import GitNexusGraph


@pytest.fixture()
def nx(sample_repo):
    data = index_repo(sample_repo)
    g = GitNexusGraph(":memory:")
    g.load(data)
    return g


def test_nodes_and_edges_recorded(nx):
    counters = dict(nx.counts())
    assert counters.get("author", 0) >= 2
    assert counters.get("commit", 0) == 2
    assert counters.get("file", 0) >= 3
    assert counters.get("symbol", 0) >= 3
    assert counters.get("authored", 0) >= 2     # author --authored--> commit
    assert counters.get("modified", 0) >= 3     # commit --modified--> file
    assert counters.get("contains", 0) >= 3     # file --contains--> symbol


def test_explain_file_returns_history_and_symbols(nx):
    qls = nx.explain_file("*", "app.py")
    assert qls["path"] == "app.py"
    assert {"greet", "Greeter"} <= {s["name"] for s in qls["symbols"]}
    assert len(qls["commits"]) == 1             # one commit touched app.py
    assert qls["commits"][0]["author_name"] == "Hari"


def test_team_activity_tallies_authors(nx):
    activity = nx.team_activity("*")
    by_author = {a["author_name"]: a["commits"] for a in activity}
    assert by_author.get("Hari") == 1 and by_author.get("Anon") == 1


def test_get_context_ranks_recent_and_relevant(nx):
    ctx = nx.get_codebase_context("*", "greeting utility")
    assert ctx["repo"] == "*"
    assert {"app.py", "util.ts"} & {f["path"] for f in ctx["top_files"]}
    assert ctx["recent_commits"], "commits present"


def test_search_memory_finds_symbols(nx):
    hits = nx.search_codebase_memory("*", "Greeter")
    assert any("app.py" == h["path"] for h in hits)
