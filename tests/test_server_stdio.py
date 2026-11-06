"""Наскрізна перевірка: MCP-клієнт запускає сервер як окремий процес (як це робить IDE)."""
import json
import sys
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parent.parent


async def _scenario(vault_path):
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "mcp_server.server"], cwd=ROOT,
        env={"VETCARE_VAULT_PATH": str(vault_path), "VETCARE_VAULT_BRANCH": "main"},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = {t.name for t in (await session.list_tools()).tools}
            first = await session.call_tool("ingest_note", {"title": "Тест MCP", "type": "decision", "content": "Текст"})
            second = await session.call_tool("ingest_note", {"title": "Тест MCP", "type": "decision", "content": "Текст"})
            found = await session.call_tool("search_notes", {"query": "пацієнт"})
            note = await session.call_tool("get_note", {"title": "Тварина"})
            return tools, first, second, found, note


def _payload(result):
    return json.loads(result.content[0].text)


def test_server_tools_over_stdio(vault):
    tools, first, second, found, note = anyio.run(_scenario, vault[0])
    assert tools == {"ingest_note", "get_note", "search_notes"}
    assert _payload(first)["status"] == "created"
    assert _payload(second)["status"] == "unchanged"
    assert "Тварина" in found.content[0].text
    assert "Пацієнт клініки" in note.content[0].text
