"""Auto-wire uctx into MCP clients (Claude Desktop, Cursor).

Detects each client's config file, backs it up, and merges in the uctx MCP
server — so a user runs one command instead of hand-editing JSON.

CLI:
    uctx setup                 # connect every detected client
    uctx setup claude          # just Claude Desktop
    uctx setup cursor          # just Cursor
    uctx setup --status        # show what's connected, change nothing

Shared by the CLI and the web UI's "Connections" panel.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path


def server_command() -> list[str]:
    """The command an MCP client should run to launch the uctx server.

    Prefers the absolute path of the installed `uctx` console script (stable
    when installed via `uv tool install` / pip). Bare `uctx` with no args runs
    the server. Falls back to the current interpreter + module.
    """
    exe = shutil.which("uctx")
    if exe:
        return [str(Path(exe).resolve())]
    return [os.path.realpath(sys.executable), "-m", "uctx.server"]


def _claude_path() -> Path:
    home = Path.home()
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if os.name == "nt":
        return Path(os.environ.get("APPDATA", home)) / "Claude" / "claude_desktop_config.json"
    return home / ".config" / "Claude" / "claude_desktop_config.json"


def _cursor_path() -> Path:
    return Path.home() / ".cursor" / "mcp.json"


TARGETS = {
    "claude": ("Claude Desktop", _claude_path),
    "cursor": ("Cursor", _cursor_path),
}


def status() -> list[dict]:
    """Per-client: detected config path, whether the app looks installed, and
    whether uctx is already wired in."""
    out = []
    for key, (name, path_fn) in TARGETS.items():
        path = path_fn()
        connected = False
        if path.exists():
            try:
                cfg = json.loads(path.read_text(encoding="utf-8"))
                connected = "uctx" in (cfg.get("mcpServers") or {})
            except Exception:
                connected = False
        # Claude: the app's dir must exist. Cursor: we can create ~/.cursor.
        installed = path.parent.exists() or key == "cursor"
        out.append({"key": key, "name": name, "path": str(path),
                    "installed": installed, "connected": connected})
    return out


def connect(key: str) -> dict:
    """Merge the uctx server into one client's config (backs up first)."""
    if key not in TARGETS:
        raise ValueError(f"unknown client {key!r}")
    name, path_fn = TARGETS[key]
    path = path_fn()
    path.parent.mkdir(parents=True, exist_ok=True)
    cfg: dict = {}
    if path.exists():
        shutil.copyfile(path, path.with_name(path.name + ".uctx-bak"))
        try:
            cfg = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
    cmd = server_command()
    cfg.setdefault("mcpServers", {})["uctx"] = {"command": cmd[0], "args": cmd[1:]}
    path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return {"name": name, "path": str(path)}


def main(argv: list[str] | None = None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)

    if "--status" in argv or "-s" in argv:
        for s in status():
            mark = "connected" if s["connected"] else ("ready" if s["installed"] else "not found")
            print(f"  {s['name']:<16} {mark:<12} {s['path']}")
        return

    requested = [a for a in argv if not a.startswith("-")] or list(TARGETS)
    cmd = server_command()
    print(f"Wiring uctx server:  {' '.join(cmd)}\n")
    any_done = False
    for key in requested:
        info = next((s for s in status() if s["key"] == key), None)
        if info is None:
            print(f"  ? unknown client: {key}")
            continue
        if not info["installed"]:
            print(f"  – {info['name']}: not found (skipped)")
            continue
        res = connect(key)
        any_done = True
        print(f"  ✓ {res['name']}: connected  ({res['path']})")
    if any_done:
        print("\nRestart the app(s) to load the uctx tools.")
    else:
        print("\nNo clients connected. Install Claude Desktop or Cursor first.")


if __name__ == "__main__":
    main()
