"""Робота з локальним клоном vault: читання, пошук та ідемпотентний запис нотаток."""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

FOLDERS = {
    "concept": "Concepts",
    "component": "Components",
    "decision": "Decisions",
    "glossary": "Glossary",
}
_FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.S)
_BAD_TITLE = re.compile(r'[\\/:*?"<>|\n\r]|\.\.')


class VaultError(Exception):
    """Помилка роботи з vault (некоректні вхідні дані чи git)."""


@dataclass
class IngestResult:
    status: str  # created | updated | unchanged
    path: str
    pushed: bool

    def as_dict(self) -> dict:
        return {"status": self.status, "path": self.path, "pushed": self.pushed}


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = _FRONT.match(text)
    if not m:
        return {}, text
    fm = dict(line.split(": ", 1) for line in m.group(1).splitlines() if ": " in line)
    return fm, text[m.end():].lstrip("\n")


def validate_title(title: str) -> str:
    title = title.strip()
    if not title or _BAD_TITLE.search(title):
        raise VaultError(f"Некоректна назва нотатки: {title!r}")
    return title


class VaultStore:
    def __init__(self, path: str | Path, branch: str = "main", remote: str = "origin", push: bool = True):
        self.root = Path(path).resolve()
        self.branch, self.remote, self.push = branch, remote, push
        if not (self.root / ".git").exists():
            raise VaultError(f"{self.root} не є git-репозиторієм")

    # ---------- git ----------
    def _git(self, *args: str, check: bool = True) -> str:
        r = subprocess.run(["git", "-C", str(self.root), *args], capture_output=True, text=True)
        if check and r.returncode != 0:
            raise VaultError(f"git {' '.join(args)}: {r.stderr.strip() or r.stdout.strip()}")
        return r.stdout

    def _remote_has_branch(self) -> bool:
        return bool(self._git("ls-remote", "--heads", self.remote, self.branch, check=False).strip())

    def sync(self) -> None:
        """Переходить на робочу гілку та підтягує зміни (git pull)."""
        current = self._git("rev-parse", "--abbrev-ref", "HEAD").strip()
        if current != self.branch:
            exists = self._git("rev-parse", "--verify", "--quiet", self.branch, check=False).strip()
            self._git("checkout", self.branch) if exists else self._git("checkout", "-b", self.branch)
        if self._remote_has_branch():
            self._git("pull", "--rebase", "--autostash", self.remote, self.branch)

    # ---------- читання ----------
    def _all_notes(self) -> dict[str, Path]:
        skip = {"Templates", "scripts", ".git"}
        return {
            p.stem: p
            for p in self.root.rglob("*.md")
            if not (set(p.relative_to(self.root).parts) & skip) and p.name != "README.md"
        }

    def get_note(self, title: str) -> str:
        notes = self._all_notes()
        title = validate_title(title)
        if title not in notes:
            raise VaultError(f"Нотатку {title!r} не знайдено")
        return notes[title].read_text(encoding="utf-8")

    def search_notes(self, query: str, limit: int = 5) -> list[dict]:
        """Базовий пошук: збіг підрядка в назві чи тексті (без урахування регістру)."""
        q = query.strip().lower()
        if not q:
            return []
        hits = []
        for title, p in sorted(self._all_notes().items()):
            text = p.read_text(encoding="utf-8")
            in_title, pos = q in title.lower(), text.lower().find(q)
            if in_title or pos >= 0:
                start = max(pos - 40, 0) if pos >= 0 else 0
                hits.append({
                    "title": title,
                    "path": str(p.relative_to(self.root)),
                    "snippet": text[start:start + 120].replace("\n", " "),
                    "_rank": 0 if in_title else 1,
                })
        hits.sort(key=lambda h: h["_rank"])
        return [{k: v for k, v in h.items() if k != "_rank"} for h in hits[:limit]]

    # ---------- запис ----------
    @staticmethod
    def render(title: str, note_type: str, content: str, links: list[str], tags: list[str], created: str) -> str:
        tag_line = ", ".join([note_type, *[t for t in tags if t != note_type]])
        body = f"# {title}\n\n{content.strip()}\n"
        if links:
            body += "\n## Зв'язки\n" + "\n".join(f"- [[{x}]]" for x in links) + "\n"
        return f"---\ntype: {note_type}\ncreated: {created}\ntags: [{tag_line}]\n---\n\n{body}"

    def ingest_note(self, title: str, type: str, content: str,
                    links: list[str] | None = None, tags: list[str] | None = None) -> IngestResult:
        if type not in FOLDERS:
            raise VaultError(f"Невідомий тип {type!r}; дозволені: {', '.join(FOLDERS)}")
        title = validate_title(title)
        links = [validate_title(x) for x in (links or [])]
        tags = tags or []
        self.sync()
        existing = self._all_notes().get(title)
        path = existing or (self.root / FOLDERS[type] / f"{title}.md")
        created = date.today().isoformat()
        if existing:
            fm, _ = parse_frontmatter(existing.read_text(encoding="utf-8"))
            created = fm.get("created", created)
        new_text = self.render(title, type, content, links, tags, created)
        rel = str(path.relative_to(self.root))
        if existing and existing.read_text(encoding="utf-8") == new_text:
            return IngestResult("unchanged", rel, False)
        status = "updated" if existing else "created"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(new_text, encoding="utf-8")
        self._git("add", rel)
        self._git("commit", "-m", f"vault: {status} {title}")
        pushed = False
        if self.push:
            self._git("push", "-u", self.remote, self.branch)
            pushed = True
        return IngestResult(status, rel, pushed)
