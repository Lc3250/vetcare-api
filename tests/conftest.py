import subprocess
from pathlib import Path

import pytest


def git(cwd, *args):
    subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True)


@pytest.fixture
def vault(tmp_path: Path):
    """Локальний клон + «віддалений» bare-репозиторій із початковою нотаткою."""
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(remote)], check=True, capture_output=True)
    work = tmp_path / "vault"
    subprocess.run(["git", "clone", str(remote), str(work)], check=True, capture_output=True)
    git(work, "config", "user.name", "Test")
    git(work, "config", "user.email", "test@example.com")
    (work / "Concepts").mkdir()
    (work / "Concepts" / "Тварина.md").write_text(
        "---\ntype: concept\ncreated: 2026-01-01\ntags: [concept]\n---\n\n# Тварина\n\nПацієнт клініки.\n",
        encoding="utf-8")
    git(work, "add", "-A")
    git(work, "commit", "-m", "init")
    git(work, "push", "-u", "origin", "main")
    return work, remote
