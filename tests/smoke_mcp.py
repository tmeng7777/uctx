"""End-to-end MCP smoke test.

Launches the uctx server as a real MCP subprocess over stdio, then acts as an
MCP *client* (like Claude Desktop would): initialize -> list tools ->
save_context -> search_context. Proves the protocol path works, not just the store.

Run:  uv run python tests/smoke_mcp.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main() -> int:
    # Use a throwaway DB so the test never touches the real ~/.uctx store.
    tmp = tempfile.mkdtemp(prefix="uctx-smoke-")
    env = {**os.environ, "UCTX_DB": os.path.join(tmp, "context.db")}

    params = StdioServerParameters(
        command=sys.executable, args=["-m", "uctx.server"], env=env
    )

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = [t.name for t in (await session.list_tools()).tools]
            print("tools:", tools)
            assert {"save_context", "search_context", "list_context", "forget_context"} <= set(tools)

            r = await session.call_tool("save_context", {
                "content": "Prefers Python and tabs over spaces",
                "type": "preference", "tags": ["coding", "style"],
                "source_app": "smoke-test",
            })
            saved = r.content[0].text
            print("save ->", saved)

            r = await session.call_tool("search_context", {"query": "Python"})
            found = r.content[0].text
            print("search 'Python' ->", found)
            assert "Python" in found, "saved item did not come back from search"

            r = await session.call_tool("search_context", {"query": "nonexistent-xyz"})
            print("search miss ->", r.content[0].text)

    print("\nOK — MCP server saved and recalled context end-to-end.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
