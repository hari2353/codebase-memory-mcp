"""Index a local git repo: commits, tree files, and a light symbol scan
(py/ts/md). Deliberately cheap (regex, no tree-sitter) — enough for file-level
memory, upgradeable later.
"""
from __future__ import annotations

import pathlib
import re
import subprocess

SYMBOL_RULES: dict[str, list[tuple[re.Pattern, str]]] = {}
for suffix, pattern, kind in (
    (".py", r"(?:async\s+)?def\s+([A-Za-z_]\w*)", "function"),
    (".py", r"\bclass\s+([A-Za-z_]\w*)", "class"),
    (".ts", r"(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)", "function"),
    (".ts", r"(?:export\s+)?class\s+([A-Za-z_$][\w$]*)", "class"),
    (".md", r"^#\s+(.{1,120}?)\s*$", "heading"),
):
    SYMBOL_RULES.setdefault(suffix, []).append((re.compile(pattern, re.M), kind))

LANGS = {".py", ".ts", ".js", ".md", ".toml"}


def _git(repo: pathlib.Path, *args: str) -> str:
    out = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
    return out.stdout


def list_files(repo: pathlib.Path) -> list[str]:
    ls = _git(repo, "ls-files", "-co", "--exclude-standard")
    return [p for p in ls.splitlines() if p]


def scan_symbols(path: str, text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    suffix = "." + path.rsplit(".", 1)[-1].lower() if "." in path else ""
    for pattern, kind in SYMBOL_RULES.get(suffix, []):
        for m in pattern.finditer(text):
            out.append((kind, m.group(1).strip()))
    seen, uniq = set(), []
    for item in out:
        if item not in seen:
            seen.add(item)
            uniq.append(item)
    return uniq


def index_repo(repo: str | pathlib.Path) -> dict:
    repo = pathlib.Path(repo).resolve()
    log = _git(repo, "log", r"--pretty=format:%H%x1f%an%x1f%ae%x1f%aI%x1f%s%x1e", "--name-only")
    commits: list[dict] = []
    # Stream layout: HEAD\x1e\n<files of commit k>\nHEAD(k+1)\x1e\n<files(k+1)>...
    # i.e. each pretty header is terminated by \x1e and the files that follow
    # belong to the header seen BEFORE them; final trailing files close the last.
    last_head: tuple[str, list[str]] | None = None
    for chunk in log.split("\x1e"):
        for line in chunk.splitlines():
            line = line.strip()
            if not line:
                continue
            if "\x1f" in line:
                if last_head is not None:
                    head, files = last_head
                    sha, an, ae, at, subject = head.split("\x1f")
                    commits.append({"sha": sha, "author_name": an, "author_email": ae,
                                    "occurred_at": at, "subject": subject,
                                    "files_changed": "\n".join(files)})
                last_head = (line, [])
            elif last_head is not None:
                last_head[1].append(line)
    if last_head is not None:
        head, files = last_head
        sha, an, ae, at, subject = head.split("\x1f")
        commits.append({"sha": sha, "author_name": an, "author_email": ae,
                        "occurred_at": at, "subject": subject,
                        "files_changed": "\n".join(files)})

    symbols: list[dict] = []
    tree: list[dict] = []
    for path in list_files(repo):
        p = repo / path
        lang = p.suffix.lstrip(".").lower() or "text"
        tree.append({"path": path, "size": p.stat().st_size, "lang": lang, "symbols": []})
        if p.suffix.lower() not in LANGS:
            continue
        text = p.read_text(errors="ignore")
        syms = scan_symbols(path, text)
        tree[-1]["symbols"] = [{"kind": k, "name": n} for k, n in syms]
        for k, n in syms:
            symbols.append({"path": path, "kind": k, "name": n})
    return {"repo": str(repo), "commits": commits, "tree": tree, "symbols": symbols}
