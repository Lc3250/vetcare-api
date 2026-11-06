"""Виклик інструмента MCP-сервера vault з командного рядка (як клієнт MCP, через stdio).

Приклад:
  python scripts/mcp_call.py search_notes '{"query": "ревакцинація"}'
"""
import json
import sys
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

ROOT = Path(__file__).resolve().parent.parent


async def call(tool: str, args: dict) -> str:
    import os

    params = StdioServerParameters(command=sys.executable, args=["-m", "mcp_server.server"], cwd=ROOT,
                                   env=dict(os.environ))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(tool, args)
            return "\n".join(c.text for c in result.content if hasattr(c, "text"))


if __name__ == "__main__":
    print(anyio.run(call, sys.argv[1], json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}))
