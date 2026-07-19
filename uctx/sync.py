"""User-owned sync — your context on every device, via a folder YOU control.

Point uctx at a folder your own cloud already syncs (Dropbox, iCloud Drive,
Google Drive) or a git repo. uctx keeps a portable `context.jsonl` snapshot
there; each machine merges it into its local store. You own the file, and
(later) it can be encrypted so the sync provider can't read it.

Why JSONL, not the raw .db: syncing a live SQLite file through cloud tools
corrupts it (partial syncs, -wal sidecars, "conflicted copy" files). A plain
JSONL export is safe to sync, human-readable, git-diffable, and mergeable.

CLI:
    uctx-sync set ~/Dropbox/uctx     # choose the synced folder (once)
    uctx-sync                        # pull remote changes in, then push yours out
    uctx-sync pull                   # merge the synced file into your local store
    uctx-sync push                   # write your local store out to the synced file
    uctx-sync status
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from . import store

CONFIG = Path(os.environ.get("UCTX_CONFIG", Path.home() / ".uctx" / "config.json"))


def sync_file() -> Path | None:
    """The path of the synced context.jsonl, from $UCTX_SYNC_DIR or the config."""
    folder = os.environ.get("UCTX_SYNC_DIR")
    if not folder and CONFIG.exists():
        folder = json.loads(CONFIG.read_text(encoding="utf-8")).get("sync_dir")
    return Path(folder).expanduser() / "context.jsonl" if folder else None


def set_sync_dir(folder: str) -> Path:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
    cfg["sync_dir"] = str(Path(folder).expanduser())
    CONFIG.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
    return sync_file()  # type: ignore[return-value]


def export_to(path: Path) -> int:
    items = store.list_all(limit=1_000_000)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for item in items:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")
    return len(items)


def import_from(path: Path) -> int:
    if not path.exists():
        return 0
    items = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return store.bulk_import(items)


def sync() -> dict:
    path = sync_file()
    if path is None:
        raise RuntimeError("No sync folder set. Run:  uctx-sync set <folder>  (or set $UCTX_SYNC_DIR)")
    pulled = import_from(path)   # remote -> local (merge)
    total = export_to(path)     # local -> remote (write back the union)
    return {"pulled": pulled, "total": total, "file": str(path)}


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(prog="uctx sync", description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd")
    p_set = sub.add_parser("set", help="choose the synced folder")
    p_set.add_argument("folder")
    sub.add_parser("pull", help="merge the synced file into your local store")
    sub.add_parser("push", help="write your local store out to the synced file")
    sub.add_parser("status", help="show the current sync file")
    args = parser.parse_args(argv)

    if args.cmd == "set":
        print(f"Sync folder set. Your context will travel via:\n  {set_sync_dir(args.folder)}")
        return
    if args.cmd == "status":
        print(f"sync file: {sync_file() or '(not set — run: uctx-sync set <folder>)'}")
        return

    path = sync_file()
    if path is None:
        raise SystemExit("No sync folder set. Run:  uctx-sync set <folder>")
    if args.cmd == "pull":
        print(f"Pulled {import_from(path)} new item(s) from {path}.")
    elif args.cmd == "push":
        print(f"Wrote {export_to(path)} item(s) to {path}.")
    else:  # default: full sync
        r = sync()
        print(f"Synced: pulled {r['pulled']} new, wrote {r['total']} total\n  {r['file']}")


if __name__ == "__main__":
    main()
