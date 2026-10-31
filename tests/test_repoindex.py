import json

from git_fixtures import sample_repo

from codebase_memory_mcp.repoindex import index_repo, list_files, scan_symbols


def test_list_files_skips_git_dir(sample_repo):
    files = list_files(sample_repo)
    assert "app.py" in files and "util.ts" in files and "docs.md" in files
    assert all(not f.startswith(".git") for f in files)


def test_scan_symbols_python_hits_def_and_class():
    symbols = scan_symbols("app.py", "def greet(name):\n\nclass Greeter:\n    pass\n")
    assert symbols == [("function", "greet"), ("class", "Greeter")]


def test_scan_symbols_ts_hits_function():
    assert scan_symbols("util.ts", "export function add(a: number) { }\nclass Foo { }") == [("function", "add"), ("class", "Foo")]


def test_index_repo_returns_commits_files_symbols(sample_repo):
    data = index_repo(sample_repo)
    assert data["repo"] == str(sample_repo)
    commits = data["commits"]
    assert len(commits) == 2
    by_subject = {c["subject"]: c for c in commits}
    f = by_subject["feat: greet and add utils"]
    assert f["author_name"] == "Hari"
    assert set(f["files_changed"].split()) >= {"app.py", "util.ts"}
    assert "app.py" in f["files_changed"] and "util.ts" in f["files_changed"]
    assert f["occurred_at"].startswith("2026-10-31")
    symbols = {s["name"] for s in data["symbols"]}
    assert {"greet", "Greeter", "add"} <= symbols
    tree = {t["path"] for t in data["tree"]}
    assert tree == {"app.py", "util.ts", "docs.md"}
