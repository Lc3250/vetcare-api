"""Тестові кейси guardrails: hook запускається окремим процесом, як це робить Claude Code."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / ".claude" / "hooks" / "guard.py"
FAKE_TOKEN = "ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2"


def run_hook(tool, **tool_input):
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps({"tool_name": tool, "tool_input": tool_input}),
                       capture_output=True, text=True, check=True)
    out = json.loads(r.stdout)["hookSpecificOutput"]
    return out["permissionDecision"], out["permissionDecisionReason"]


ALLOW = [
    ("A-01", "Read", {"file_path": "/repo/core/vaccination_schedule.py"}),
    ("A-02", "Bash", {"command": "pytest -q"}),
    ("A-02", "Bash", {"command": "ruff check ."}),
    ("A-03", "mcp__vetcare-kb__search_notes", {"query": "ревакцинація"}),
    ("A-04", "Bash", {"command": "git status && git diff"}),
]
WARN = [
    ("W-01", "Write", {"file_path": "/repo/core/overdue.py", "content": "x = 1"}),
    ("W-02", "Bash", {"command": "git commit -m 'feat: тест'"}),
    ("W-03", "Edit", {"file_path": "/repo/README.md", "new_string": "текст"}),
    ("W-04", "Bash", {"command": "pip install requests"}),
    ("W-05", "mcp__vetcare-kb__ingest_note", {"title": "Х", "type": "decision", "content": "т"}),
]
BLOCK = [
    ("B-01", "Bash", {"command": "git push origin main"}),
    ("B-02", "Bash", {"command": "rm -rf Decisions/"}),
    ("B-03", "Bash", {"command": "git push --force origin praktychna-4"}),
    ("B-04", "Bash", {"command": "git reset --hard HEAD~1"}),
    ("B-05", "Write", {"file_path": "/repo/config.py", "content": f'TOKEN = "{FAKE_TOKEN}"'}),
    ("B-06", "Read", {"file_path": "/home/user/vetcare-knowledge-base/Concepts/Тварина.md"}),
    ("B-06", "Bash", {"command": "grep -r ревакцинація ../vetcare-knowledge-base"}),
]


@pytest.mark.parametrize("rule,tool,args", ALLOW)
def test_allow(rule, tool, args):
    kind, reason = run_hook(tool, **args)
    assert kind == "allow", reason


@pytest.mark.parametrize("rule,tool,args", WARN)
def test_warn_requires_approval(rule, tool, args):
    kind, reason = run_hook(tool, **args)
    assert kind == "ask" and f"[{rule}]" in reason


@pytest.mark.parametrize("rule,tool,args", BLOCK)
def test_block(rule, tool, args):
    kind, reason = run_hook(tool, **args)
    assert kind == "deny" and f"[{rule}]" in reason


def test_branch_push_is_not_blocked():
    kind, _ = run_hook("Bash", command="git push -u origin praktychna-4")
    assert kind == "allow"


def test_git_pre_commit_blocks_main_and_secrets(tmp_path):
    def git(*a, env=None):
        return subprocess.run(["git", "-C", str(tmp_path), *a], capture_output=True, text=True, env=env)

    subprocess.run(["git", "init", "-q", "-b", "main", str(tmp_path)], check=True)
    git("config", "user.name", "T")
    git("config", "user.email", "t@e.com")
    git("config", "core.hooksPath", str(ROOT / "scripts" / "git-hooks"))
    (tmp_path / "a.txt").write_text("ok", encoding="utf-8")
    git("add", "a.txt")
    r = git("commit", "-m", "x")
    assert r.returncode != 0 and "B-01" in r.stderr
    git("checkout", "-q", "-b", "feature")
    assert git("commit", "-m", "x").returncode == 0
    (tmp_path / "b.txt").write_text(f"token={FAKE_TOKEN}", encoding="utf-8")
    git("add", "b.txt")
    r = git("commit", "-m", "y")
    assert r.returncode != 0 and "B-05" in r.stderr
