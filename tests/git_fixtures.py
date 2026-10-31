import subprocess
import os
from pathlib import Path

import pytest


def run_git(cwd: Path, *args: str, env_user: str = "Dev A", env_email: str = "a@x.dev"):
    env = dict(os.environ)
    env.update({"GIT_AUTHOR_NAME": env_user, "GIT_AUTHOR_EMAIL": env_email,
                "GIT_COMMITTER_NAME": env_user, "GIT_COMMITTER_EMAIL": env_email,
                "GIT_AUTHOR_DATE": "2026-10-31T09:00:00 +0000",
                "GIT_COMMITTER_DATE": "2026-10-31T09:00:00 +0000"})
    subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True)


@pytest.fixture(scope="session")
def sample_repo(tmp_path_factory) -> Path:
    """Tiny repo: two commits, python + ts files, one author each."""
    root = tmp_path_factory.mktemp("repo")
    run_git(root, "init", "-q", "-b", "main")
    (root / "app.py").write_text("def greet(name):\n    return f'hi {name}'\n\n\nclass Greeter:\n    pass\n")
    (root / "util.ts").write_text("export function add(a: number, b: number): number {\n  return a + b;\n}\n")
    run_git(root, "add", ".")
    run_git(root, "commit", "-q", "-m", "feat: greet and add utils", env_user="Hari", env_email="h@x.dev")
    (root / "docs.md").write_text("# readme\n")
    run_git(root, "add", ".")
    run_git(root, "commit", "-q", "-m", "docs: readme", env_user="Anon", env_email="n@x.dev")
    return root
