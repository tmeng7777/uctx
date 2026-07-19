"""uctx MCP server.

Exposes the local context store as MCP tools so ANY MCP-enabled agent
(Claude Desktop, Cursor, …) can read and write the *same* user-owned context.
Point two different agents at this one server and they share memory.

Run:  uctx           (installed script)
  or: python -m uctx.server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import store

mcp = FastMCP("uctx")


def _fmt(item: dict) -> str:
    line = f"#{item['id']} [{item['type']}] {item['content']}"
    if item.get("tags"):
        line += f"  ·tags: {item['tags']}"
    line += f"  ·from {item['source_app']} @ {item['created_at'][:10]}"
    return line


@mcp.tool()
def save_context(content: str, type: str = "note", tags: list[str] | None = None,
                 source_app: str = "unknown") -> str:
    """Save a durable fact, preference, or note about the user so any agent can recall it later.

    Use this whenever the user states something worth remembering across sessions and tools
    (e.g. "I prefer Python", "I'm based in Boston", "my project is a job-hunting agent").

    Args:
        content: The thing to remember, in a self-contained sentence.
        type: One of "preference", "fact", or "note".
        tags: Optional short keywords to aid later search (e.g. ["coding", "style"]).
        source_app: The app/agent saving this (e.g. "claude-desktop", "cursor").
    """
    item_id = store.save(content, type=type, tags=tags, source_app=source_app)
    return f"Saved context #{item_id}: {content}"


@mcp.tool()
def search_context(query: str, limit: int = 10) -> str:
    """Search the user's saved context by keyword.

    Call this BEFORE answering questions about the user's preferences, background, or history,
    so your answer reflects what they've told other agents — not just this conversation.
    """
    items = store.search(query, limit=limit)
    if not items:
        return f"No saved context matched '{query}'."
    return "\n".join(_fmt(i) for i in items)


@mcp.tool()
def list_context(limit: int = 50) -> str:
    """List the user's saved context items, most recent first."""
    items = store.list_all(limit=limit)
    if not items:
        return "No context saved yet."
    return "\n".join(_fmt(i) for i in items)


@mcp.tool()
def forget_context(item_id: int) -> str:
    """Delete one saved context item by its id (from list_context/search_context)."""
    ok = store.forget(item_id)
    return f"Deleted context #{item_id}." if ok else f"No context found with id #{item_id}."


def run_server() -> None:
    mcp.run()


HELP = """uctx — portable, local, user-owned context

Usage:
  uctx                       run the MCP server (what your AI agents call)
  uctx setup [claude|cursor] wire uctx into your AI clients (auto-config)
  uctx web                   open the local dashboard (view/edit/sync context)
  uctx sync [set|pull|push]  sync your context across devices
  uctx --version
"""


def main() -> None:
    import sys

    args = sys.argv[1:]
    if not args or args[0] in ("serve", "server"):
        run_server()
        return
    cmd = args[0]
    if cmd in ("-h", "--help", "help"):
        print(HELP)
    elif cmd in ("-V", "--version", "version"):
        from . import __version__
        print(f"uctx {__version__}")
    elif cmd == "setup":
        from .setup import main as setup_main
        setup_main(args[1:])
    elif cmd == "web":
        from .web import main as web_main
        web_main()
    elif cmd == "sync":
        from .sync import main as sync_main
        sync_main(args[1:])
    else:
        print(f"uctx: unknown command {cmd!r} — try `uctx --help`")


if __name__ == "__main__":
    main()
