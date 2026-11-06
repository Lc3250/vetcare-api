# Guardrails (ПР4)

Деталізація первинних категорій із ПР1. Правила застосовує hook `.claude/hooks/guard.py` (PreToolUse у Claude Code), частину дублює git pre-commit (`scripts/git-hooks/pre-commit`).

## Allow (виконується без підтвердження)
| ID | Правило |
|----|---------|
| A-01 | читання та пошук по файлах застосунку (Read, Grep, Glob) |
| A-02 | запуск тестів і лінтера (`pytest`, `ruff`) |
| A-03 | читання vault через MCP (`search_notes`, `get_note`) |
| A-04 | перегляд стану git (`status`, `diff`, `log`) |

## Warn (потрібне підтвердження людини)
| ID | Правило |
|----|---------|
| W-01 | створення чи зміна файлів у `core/` і `storage/` |
| W-02 | `git commit` |
| W-03 | створення чи зміна будь-яких інших файлів |
| W-04 | встановлення залежностей (`pip install`, `npm install`, `uv add`) |
| W-05 | запис у vault (`ingest_note`, `link_notes`) |

## Block (заборонено безумовно)
| ID | Правило |
|----|---------|
| B-01 | прямий `git push` у `main`/`master`, прямий коміт у `main` (git pre-commit) |
| B-02 | видалення файлів і нотаток (`rm`, `git rm`, `rmdir`, `unlink`), зокрема в `Decisions/` |
| B-03 | `git push --force` та його варіанти |
| B-04 | зміна історії git (`reset --hard`, `rebase`, `commit --amend`, `filter-branch`) |
| B-05 | секрети (токени, ключі, паролі) у командах і вмісті файлів, а також у комітах (git pre-commit) |
| B-06 | прямий доступ до файлів vault в обхід MCP (Read/Grep/Glob/Write/Edit або `cat`/`grep`/`ls` по шляху vault) |

## Механізм
Hook отримує JSON із назвою інструмента й аргументами та повертає `deny` (block), `ask` (warn) або `allow`. Розрізнення за шляхом vault спирається на підрядок `knowledge-base` у назві каталогу клону.

## Обмеження
Hook аналізує текст команди, тому його можна обійти непрямими способами (скрипт, що сам видаляє файли). Для навчального проєкту це прийнятно; другий рубіж – git pre-commit і захист гілки `main` на GitHub.
