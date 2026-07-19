"""Two-machine sync test (offline, deterministic).

Simulates a laptop and a phone that each have their own local store but share
one synced folder. Proves the union converges: after both sync, both machines
have all items.

Run:  uv run python tests/sync_test.py
"""

from __future__ import annotations

import importlib
import os
import tempfile
from pathlib import Path

work = Path(tempfile.mkdtemp(prefix="uctx-sync-"))
shared = work / "shared"          # stands in for ~/Dropbox/uctx
shared.mkdir()
laptop_db = work / "laptop.db"
phone_db = work / "phone.db"


def as_machine(db: Path):
    """Point the store + sync modules at one machine's DB and the shared folder."""
    os.environ["UCTX_DB"] = str(db)
    os.environ["UCTX_SYNC_DIR"] = str(shared)
    import uctx.store as store
    import uctx.sync as sync
    importlib.reload(store)
    sync = importlib.reload(sync)
    return store, sync


def contents(store) -> set[str]:
    return {i["content"] for i in store.list_all(limit=1000)}


def main() -> int:
    # Laptop saves two things and syncs out.
    store, sync = as_machine(laptop_db)
    store.save("Prefers Python and tabs", type="preference", source_app="laptop")
    store.save("Based in Boston", type="fact", source_app="laptop")
    r = sync.sync()
    print("laptop sync:", r["pulled"], "pulled,", r["total"], "total")

    # Phone starts empty, syncs -> should pull the laptop's items.
    store, sync = as_machine(phone_db)
    assert contents(store) == set(), "phone should start empty"
    r = sync.sync()
    print("phone sync:", r["pulled"], "pulled,", r["total"], "total")
    assert "Prefers Python and tabs" in contents(store), "phone should receive laptop's context"

    # Phone adds one, syncs out.
    store.save("Learning agentic frameworks", type="note", source_app="phone")
    sync.sync()

    # Laptop syncs again -> should now have the phone's item too.
    store, sync = as_machine(laptop_db)
    sync.sync()
    both = contents(store)
    print("laptop now has:", sorted(both))
    assert both == {"Prefers Python and tabs", "Based in Boston", "Learning agentic frameworks"}

    # Re-syncing is a no-op (dedupe by content+type).
    r = sync.sync()
    assert r["pulled"] == 0, "re-sync should add nothing"

    print("\nOK — two machines converged to the same context via one owned folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
