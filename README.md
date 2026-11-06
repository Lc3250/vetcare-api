# VetCare API

Навчальний застосунок (облік пацієнтів ветеринарної клініки) і супровідний agent harness. Вимоги: [ЗАВДАННЯ.md](ЗАВДАННЯ.md), [docs/](docs/).

База знань лежить в окремому репозиторії [vetcare-knowledge-base](https://github.com/Lc3250/vetcare-knowledge-base); агент працює з нею лише через MCP-сервер `mcp_server/`.

## Запуск тестів
```
pip install -r requirements.txt
pytest
ruff check .
```
