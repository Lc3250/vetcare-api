# Підключення GitHub MCP-сервера (ПР3, завдання 4)

Токен створює та зберігає сам студент; у репозиторій токен не потрапляє.

1. GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token.
2. Repository access: **Only select repositories** → `vetcare-api`.
3. Permissions (лише читання): Contents – Read-only, Pull requests – Read-only, Issues – Read-only, Metadata – Read-only. Інших прав не надавати.
4. Зберегти токен у змінній середовища `GITHUB_MCP_TOKEN` (не в репозиторії).
5. Додати вміст `.mcp.github.example.json` у `.mcp.json` (секція `mcpServers`) або виконати:
   `claude mcp add --transport http github https://api.githubcopilot.com/mcp/ -H "Authorization: Bearer $GITHUB_MCP_TOKEN"`.
6. У Claude Code командою `/mcp` переконатися, що `vetcare-kb` і `github` мають статус connected.
7. Попросити агента отримати 2–3 останні коміти через інструменти GitHub MCP (наприклад, `list_commits`) і передати їх у `ingest_note` як нотатки типу decision.

## Спостереження для звіту
Після виконання кроків 6–7 варто зафіксувати: які інструменти GitHub MCP викликав агент, чи не створилося дублікатів у vault, які права має токен.
