"""MCP-сервер конектора до бази знань VetCare (vault).

Налаштування через змінні середовища:
  VETCARE_VAULT_PATH    шлях до локального клону репозиторію vault (обов'язково)
  VETCARE_VAULT_BRANCH  робоча гілка vault (за замовчуванням main)
  VETCARE_VAULT_PUSH    0, щоб не виконувати git push (за замовчуванням 1)
"""
from __future__ import annotations

import os

from mcp.server.mcpserver import MCPServer

from mcp_server.vault_store import VaultError, VaultStore

mcp = MCPServer("vetcare-kb")
_store: VaultStore | None = None


def store() -> VaultStore:
    global _store
    if _store is None:
        path = os.environ.get("VETCARE_VAULT_PATH")
        if not path:
            raise VaultError("Не задано VETCARE_VAULT_PATH")
        _store = VaultStore(
            path,
            branch=os.environ.get("VETCARE_VAULT_BRANCH", "main"),
            push=os.environ.get("VETCARE_VAULT_PUSH", "1") != "0",
        )
    return _store


@mcp.tool()
def ingest_note(title: str, type: str, content: str,
                links: list[str] | None = None, tags: list[str] | None = None) -> dict:
    """Створює або оновлює нотатку у vault, комітить і пушить зміни.

    type: concept | component | decision | glossary.
    links: назви нотаток, на які треба послатися (записуються як wiki-посилання).
    Повторний виклик з тими самими даними повертає status=unchanged.
    """
    return store().ingest_note(title, type, content, links, tags).as_dict()


@mcp.tool()
def link_notes(title: str, relation: str, targets: list[str]) -> dict:
    """Додає типізований зв'язок у frontmatter нотатки.

    relation: depends_on | implements | supersedes | belongs_to.
    targets: назви наявних нотаток. Повторний виклик не змінює нотатку.
    """
    return store().add_relation(title, relation, targets).as_dict()


@mcp.tool()
def get_note(title: str) -> str:
    """Повертає повний текст нотатки за точною назвою (без розширення)."""
    return store().get_note(title)


@mcp.tool()
def search_notes(query: str, limit: int = 5) -> list[dict]:
    """Шукає нотатки за запитом і повертає назву, шлях та уривок."""
    return store().search_notes(query, limit)


if __name__ == "__main__":
    mcp.run()
