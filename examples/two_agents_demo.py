"""Runnable proof of the whole idea: two *different* agents, one context you own.

Agent A ("claude-desktop") saves some context over MCP. Then a brand-new agent
B ("cursor") connects to the SAME local store and recalls it — even though B
never saw A's conversation. No cloud; just a local file both agents share.

Run:  uv run python examples/two_agents_demo.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run_agent(name: str, env: dict, actions: list[tuple[str, dict]]) -> None:
    params = StdioServerParameters(command=sys.executable, args=["-m", "uctx.server"], env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for tool, args in actions:
                res = await session.call_tool(tool, args)
                text = res.content[0].text.replace("\n", "\n           ")
                shown = args.get("content") or args.get("query") or ""
                print(f"  [{name}] {tool}({shown!r})\n           -> {text}")


async def main() -> None:
    tmp = tempfile.mkdtemp(prefix="uctx-demo-")
    env = {**os.environ, "UCTX_DB": os.path.join(tmp, "context.db")}

    print("Agent A = 'claude-desktop'  — saves what the user tells it:\n")
    await run_agent("claude-desktop", env, [
        ("save_context", {"content": "Prefers Python, tabs over spaces", "type": "preference",
                          "tags": ["coding", "style"], "source_app": "claude-desktop"}),
        ("save_context", {"content": "Based in Boston", "type": "fact", "source_app": "claude-desktop"}),
        ("save_context", {"content": "Learning agentic frameworks", "type": "note", "source_app": "claude-desktop"}),
    ])

    print("\n" + "-" * 64)
    print("Switch apps. Brand-new agent, same local store, no shared chat.")
    print("-" * 64 + "\n")

    print("Agent B = 'cursor'  — recalls it without ever seeing the above:\n")
    await run_agent("cursor", env, [
        ("search_context", {"query": "coding"}),
        ("list_context", {}),
    ])

    print("\n=>  Two different agents. One context you own.")


if __name__ == "__main__":
    asyncio.run(main())
