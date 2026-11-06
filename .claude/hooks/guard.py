#!/usr/bin/env python3
"""PreToolUse-hook Claude Code: застосовує guardrails з docs/guardrails.md.

Вхід (stdin): JSON з полями tool_name, tool_input, cwd.
Вихід: JSON із hookSpecificOutput.permissionDecision = allow | ask | deny.
Правило B-xx блокує (deny), W-xx вимагає підтвердження (ask), решта дозволена (allow).
"""
from __future__ import annotations

import json
import re
import sys

VAULT_HINT = re.compile(r"knowledge-base", re.I)
SECRET = re.compile(
    r"(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|(?:api[_-]?key|secret|token|password)\s*[=:]\s*['\"][^'\"]{8,}['\"])",
    re.I)
CORE_PATH = re.compile(r"(^|/)(core|storage)/")
VAULT_READ_CMD = re.compile(r"\b(cat|less|more|head|tail|grep|rg|find|ls|sed|awk|tree)\b")


def decision(kind: str, rule: str, reason: str) -> dict:
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": kind,
                                   "permissionDecisionReason": f"[{rule}] {reason}"}}


def check_bash(cmd: str) -> dict | None:
    if re.search(r"git\s+push\b.*(--force\b|--force-with-lease|\s-f\b|\+\S)", cmd):
        return decision("deny", "B-03", "force-push заборонено")
    if re.search(r"git\s+push\b[^|;&]*\b(origin\s+)?(HEAD:)?(main|master)\b", cmd):
        return decision("deny", "B-01", "прямий push у main заборонено; використовуйте гілку та pull request")
    if re.search(r"git\s+(reset\s+--hard|rebase|filter-branch|commit\s+--amend)", cmd):
        return decision("deny", "B-04", "зміна історії git заборонена")
    if re.search(r"\brm\b|\bgit\s+rm\b|\brmdir\b|\bunlink\b|\bshred\b", cmd):
        return decision("deny", "B-02", "видалення файлів заборонено (перенесіть у _to_delete/ та запитайте людину)")
    if VAULT_HINT.search(cmd) and VAULT_READ_CMD.search(cmd):
        return decision("deny", "B-06", "vault доступний лише через MCP-конектор")
    if SECRET.search(cmd):
        return decision("deny", "B-05", "у команді виявлено секрет")
    if re.search(r"git\s+commit\b", cmd):
        return decision("ask", "W-02", "коміт потребує підтвердження")
    if re.search(r"\b(pip|pip3|npm|uv)\s+(install|add)\b", cmd):
        return decision("ask", "W-04", "встановлення залежностей потребує підтвердження")
    return None


def check_file_tool(tool: str, ti: dict) -> dict | None:
    path = ti.get("file_path") or ti.get("path") or ""
    if VAULT_HINT.search(path):
        return decision("deny", "B-06", "прямий доступ до файлів vault заборонено; використовуйте MCP-інструменти")
    if tool in ("Write", "Edit", "NotebookEdit"):
        content = ti.get("content") or ti.get("new_string") or ""
        if SECRET.search(content):
            return decision("deny", "B-05", "у вмісті виявлено секрет")
        if CORE_PATH.search(path.replace("\\", "/")):
            return decision("ask", "W-01", "зміна шарів core/ чи storage/ потребує підтвердження")
        return decision("ask", "W-03", "зміна файлів потребує підтвердження")
    return None


def evaluate(event: dict) -> dict:
    tool, ti = event.get("tool_name", ""), event.get("tool_input", {}) or {}
    result = None
    if tool == "Bash":
        result = check_bash(ti.get("command", ""))
    elif tool in ("Read", "Grep", "Glob", "Write", "Edit", "NotebookEdit"):
        result = check_file_tool(tool, ti)
    elif tool in ("mcp__vetcare-kb__ingest_note", "mcp__vetcare-kb__link_notes"):
        result = decision("ask", "W-05", "запис у vault потребує підтвердження")
    return result or decision("allow", "A-01", "дія дозволена")


if __name__ == "__main__":
    print(json.dumps(evaluate(json.load(sys.stdin)), ensure_ascii=False))
