import builtins

import pytest

from mcp_server.vault_store import VaultStore
from mcp_server.vector_index import LsaEmbedder, VectorIndex, chunk_note, make_embedder

NOTES = {
    "Ревакцинація": "Повторне щеплення тією ж вакциною через визначений інтервал, щоб підтримати імунітет.",
    "Власник": "Людина, яка привела тварину до клініки та відповідає за її лікування.",
    "ADR-001 Використання SQLite": "## Контекст\nПотрібне сховище без окремого сервера БД.\n\n## Рішення\nВикористовуємо SQLite.",
    "Візит": "Одне звернення до клініки: дата, причина, діагноз, нотатки лікаря.",
    "Серія вакцини": "Виробничий номер партії препарату, який записують під час вакцинації.",
}


@pytest.fixture
def mini_vault(tmp_path):
    for title, body in NOTES.items():
        (tmp_path / f"{title}.md").write_text(f"---\ntype: concept\ncreated: 2026-01-01\ntags: [x]\n---\n\n# {title}\n\n{body}\n",
                                              encoding="utf-8")
    (tmp_path / ".git").mkdir()
    return tmp_path


def test_chunk_note_splits_by_headings_and_prefixes_title():
    text = "---\ntype: decision\n---\n\n# ADR\n\n## Контекст\nА\n\n## Рішення\nБ\n"
    chunks = chunk_note("ADR", "Decisions/ADR.md", text)
    assert [c.text for c in chunks] == ["ADR. ## Контекст\nА", "ADR. ## Рішення\nБ"]
    assert "type:" not in "".join(c.text for c in chunks)


def test_chunk_note_without_headings_is_single_chunk():
    chunks = chunk_note("Власник", "Concepts/Власник.md", "---\ntype: concept\n---\n\n# Власник\n\nОпис.\n")
    assert len(chunks) == 1 and chunks[0].text.startswith("Власник. Опис")


def test_search_finds_note_by_inflected_form(mini_vault):
    idx = VectorIndex.build(mini_vault, LsaEmbedder())
    assert idx.search("ревакцинації", 3)[0]["title"] == "Ревакцинація"


def test_search_returns_scores_sorted_and_limited(mini_vault):
    hits = VectorIndex.build(mini_vault, LsaEmbedder()).search("база даних SQLite", 3)
    assert len(hits) == 3 and hits[0]["title"] == "ADR-001 Використання SQLite"
    assert [h["score"] for h in hits] == sorted((h["score"] for h in hits), reverse=True)


def test_index_is_persisted_and_rebuilt_when_vault_changes(mini_vault, tmp_path):
    index_dir = tmp_path / "idx"
    first = VectorIndex.load_or_build(mini_vault, index_dir, kind="lsa")
    again = VectorIndex.load_or_build(mini_vault, index_dir, kind="lsa")
    assert again.fp == first.fp
    new_note = "---\ntype: concept\ncreated: 2026-01-01\ntags: [x]\n---\n\n# Нова\n\nМікрочіп тварини.\n"
    (mini_vault / "Нова.md").write_text(new_note, encoding="utf-8")
    rebuilt = VectorIndex.load_or_build(mini_vault, index_dir, kind="lsa")
    assert rebuilt.fp != first.fp
    assert rebuilt.search("мікрочіп", 1)[0]["title"] == "Нова"


def test_store_search_notes_uses_vector_by_default_and_exact_on_request(mini_vault, tmp_path):
    vector = VaultStore(mini_vault, push=False, index_dir=tmp_path / "i")
    assert vector.search_mode == "vector"
    assert vector.search_notes("ревакцинації", 1)[0]["title"] == "Ревакцинація"
    exact = VaultStore(mini_vault, push=False, search_mode="exact", index_dir=tmp_path / "i2")
    assert exact.search_notes("ревакцинації", 1) == []  # збіг підрядка форму слова не знаходить


def test_empty_query_returns_nothing(mini_vault, tmp_path):
    assert VaultStore(mini_vault, index_dir=tmp_path / "i").search_notes("   ") == []


def test_make_embedder_falls_back_to_lsa_without_sentence_transformers(monkeypatch):
    real_import = builtins.__import__

    def fake(name, *a, **kw):
        if name.startswith("sentence_transformers"):
            raise ImportError(name)
        return real_import(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", fake)
    assert make_embedder("auto").name == "lsa"
    with pytest.raises(ImportError):
        make_embedder("st")
