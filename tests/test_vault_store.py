import subprocess
from datetime import date

import pytest

from mcp_server.vault_store import VaultError, VaultStore


def run_git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def commits(path):
    return int(run_git("-C", str(path), "rev-list", "--count", "HEAD"))


def test_ingest_creates_note_in_type_folder(vault):
    work, _ = vault
    r = VaultStore(work).ingest_note("Тестове рішення", "decision", "Текст", links=["Тварина"])
    assert r.status == "created" and r.path == "Decisions/Тестове рішення.md" and r.pushed
    text = (work / r.path).read_text(encoding="utf-8")
    assert "type: decision" in text and "[[Тварина]]" in text


def test_ingest_is_idempotent(vault):
    work, _ = vault
    s = VaultStore(work)
    s.ingest_note("Рішення А", "decision", "Текст")
    n = commits(work)
    again = s.ingest_note("Рішення А", "decision", "Текст")
    assert again.status == "unchanged" and commits(work) == n
    assert len(list((work / "Decisions").glob("*.md"))) == 1


def test_ingest_updates_changed_note_and_keeps_created(vault):
    work, _ = vault
    s = VaultStore(work)
    s.ingest_note("Рішення Б", "decision", "Старий текст")
    path = work / "Decisions" / "Рішення Б.md"
    old = path.read_text(encoding="utf-8")
    path.write_text(old.replace(f"created: {date.today().isoformat()}", "created: 2026-02-02"), encoding="utf-8")
    run_git("-C", str(work), "commit", "-am", "date")
    r = s.ingest_note("Рішення Б", "decision", "Новий текст")
    assert r.status == "updated"
    assert "created: 2026-02-02" in path.read_text(encoding="utf-8")
    assert "Новий текст" in path.read_text(encoding="utf-8")


def test_push_reaches_remote(vault):
    work, remote = vault
    VaultStore(work).ingest_note("Рішення В", "decision", "Текст")
    out = run_git("--git-dir", str(remote), "log", "--oneline", "main")
    assert "vault: created Рішення В" in out


def test_ingest_on_separate_branch(vault):
    work, remote = vault
    VaultStore(work, branch="praktychna-x").ingest_note("Рішення Г", "decision", "Текст")
    heads = run_git("--git-dir", str(remote), "branch")
    assert "praktychna-x" in heads


@pytest.mark.parametrize("title", ["../evil", "a/b", "", "x\ny"])
def test_rejects_bad_titles(vault, title):
    with pytest.raises(VaultError):
        VaultStore(vault[0]).ingest_note(title, "decision", "x")


def test_rejects_unknown_type(vault):
    with pytest.raises(VaultError):
        VaultStore(vault[0]).ingest_note("Назва", "unknown", "x")


def test_get_note_and_missing(vault):
    s = VaultStore(vault[0])
    assert "Пацієнт клініки" in s.get_note("Тварина")
    with pytest.raises(VaultError):
        s.get_note("Немає такої")


def test_search_notes_exact_substring(vault):
    s = VaultStore(vault[0])
    hits = s.search_notes("пацієнт")
    assert [h["title"] for h in hits] == ["Тварина"]
    assert s.search_notes("зовсім відсутнє слово") == []


def test_new_note_is_registered_in_moc(vault):
    work, _ = vault
    (work / "MOC-Застосунок.md").write_text(
        "---\ntype: moc\ncreated: 2026-01-01\ntags: [moc]\n---\n\n# MOC\n\n"
        "## Рішення\n- [[Старе]]\n\n## Глосарій\n- [[Термін]]\n",
        encoding="utf-8")
    run_git("-C", str(work), "add", "-A")
    run_git("-C", str(work), "commit", "-m", "moc")
    s = VaultStore(work)
    s.ingest_note("Нове рішення", "decision", "Текст")
    moc = (work / "MOC-Застосунок.md").read_text(encoding="utf-8")
    assert moc.index("[[Нове рішення]]") < moc.index("## Глосарій")
    s.ingest_note("Нове рішення", "decision", "Текст")
    assert (work / "MOC-Застосунок.md").read_text(encoding="utf-8").count("[[Нове рішення]]") == 1


def test_unpushed_commit_is_pushed_on_repeat_call(vault, tmp_path):
    work, remote = vault
    run_git("-C", str(work), "remote", "set-url", "origin", str(tmp_path / "nowhere.git"))
    s = VaultStore(work)
    with pytest.raises(VaultError):
        s.ingest_note("Рішення Д", "decision", "Текст")
    run_git("-C", str(work), "remote", "set-url", "origin", str(remote))
    r = s.ingest_note("Рішення Д", "decision", "Текст")
    assert r.status == "unchanged" and r.pushed
    assert "vault: created Рішення Д" in run_git("--git-dir", str(remote), "log", "--oneline", "main")


def test_add_relation_is_idempotent_and_survives_ingest(vault):
    work, _ = vault
    s = VaultStore(work)
    s.ingest_note("Компонент Х", "component", "Опис")
    first = s.add_relation("Компонент Х", "depends_on", ["Тварина"])
    n = commits(work)
    again = s.add_relation("Компонент Х", "depends_on", ["Тварина"])
    assert first.status == "updated" and again.status == "unchanged" and commits(work) == n
    s.ingest_note("Компонент Х", "component", "Оновлений опис")
    text = (work / "Components" / "Компонент Х.md").read_text(encoding="utf-8")
    assert 'depends_on: ["Тварина"]' in text and "Оновлений опис" in text


def test_add_relation_validates_input(vault):
    s = VaultStore(vault[0])
    with pytest.raises(VaultError):
        s.add_relation("Тварина", "likes", ["Тварина"])
    with pytest.raises(VaultError):
        s.add_relation("Тварина", "belongs_to", ["Немає такої"])
    with pytest.raises(VaultError):
        s.add_relation("Немає такої", "belongs_to", ["Тварина"])


def test_ingest_meta_fields_are_written_and_preserved_on_update(vault):
    work, _ = vault
    s = VaultStore(work)
    s.ingest_note("Компонент М", "component", "Опис", meta={"path": "core/x.py", "layer": "core"})
    s.ingest_note("Компонент М", "component", "Новий опис")
    text = (work / "Components" / "Компонент М.md").read_text(encoding="utf-8")
    assert "path: core/x.py" in text and "layer: core" in text and "Новий опис" in text


@pytest.mark.parametrize("key", ["type", "Bad Key", "a\nb"])
def test_ingest_rejects_bad_meta_keys(vault, key):
    with pytest.raises(VaultError):
        VaultStore(vault[0]).ingest_note("Назва М", "component", "x", meta={key: "v"})
