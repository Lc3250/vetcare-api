# Тестові кейси guardrails (ПР4)

Автоматично виконуються командою `pytest tests/test_guard.py`: hook запускається окремим процесом із JSON на stdin, як це робить Claude Code. Результат останнього запуску: **19 кейсів, усі пройшли** (разом із рештою набору 36 тестів).

## Allow
| Правило | Сценарій | Очікувана реакція |
|---------|----------|-------------------|
| A-01 | Read `core/vaccination_schedule.py` | allow |
| A-02 | Bash `pytest -q`; Bash `ruff check .` | allow |
| A-03 | MCP `search_notes` | allow |
| A-04 | Bash `git status && git diff` | allow |

## Warn
| Правило | Сценарій | Очікувана реакція |
|---------|----------|-------------------|
| W-01 | Write у `core/overdue.py` | ask |
| W-02 | Bash `git commit -m ...` | ask |
| W-03 | Edit `README.md` | ask |
| W-04 | Bash `pip install requests` | ask |
| W-05 | MCP `ingest_note` | ask |

## Block
| Правило | Сценарій | Очікувана реакція |
|---------|----------|-------------------|
| B-01 | Bash `git push origin main` | deny |
| B-02 | Bash `rm -rf Decisions/` | deny |
| B-03 | Bash `git push --force origin praktychna-4` | deny |
| B-04 | Bash `git reset --hard HEAD~1` | deny |
| B-05 | Write файлу з рядком `TOKEN = "ghp_..."` (тестове значення) | deny |
| B-06 | Read файлу в `vetcare-knowledge-base/`; Bash `grep -r ... ../vetcare-knowledge-base` | deny |

## Додатково
- `git push -u origin praktychna-4` (push у гілку) не блокується.
- Git pre-commit: коміт у `main` відхилено (B-01), коміт із токеном відхилено (B-05), звичайний коміт у feature-гілці дозволено. Під час написання тесту виявлено, що хук не спрацьовував у репозиторії без жодного коміту; виправлено заміною `rev-parse` на `symbolic-ref`.

## Як перевірити вручну у Claude Code
Відкрити репозиторій у Claude Code та попросити агента виконати `git push origin main`: дія має бути заблокована повідомленням `[B-01]`. Підключення git-хука: `scripts/install-git-hooks.sh`.
