"""Semantic search test (offline, deterministic).

Uses the dependency-free `stub` embedder so this runs anywhere with no API key.
Proves the mechanism: embeddings are stored, cosine ranking works, and a query
retrieves the relevant item ahead of unrelated ones. Real synonym matching comes
from the openai/gemini providers (not exercised here).

Run:  UCTX_EMBEDDER=stub uv run python tests/semantic_test.py
"""

from __future__ import annotations

import os
import tempfile

os.environ.setdefault("UCTX_EMBEDDER", "stub")
os.environ["UCTX_DB"] = os.path.join(tempfile.mkdtemp(prefix="uctx-sem-"), "context.db")

from uctx import embeddings, store  # noqa: E402  (env must be set first)


def main() -> int:
    embed = embeddings.get_embedder()
    assert embed is not None, "stub embedder should be active"

    def save(text: str, **kw) -> int:
        return store.save(text, embedding=embed([text])[0], **kw)

    save("Prefers Python and tabs over spaces", type="preference", tags=["coding"])
    save("Based in Boston", type="fact")
    save("Enjoys hiking on weekends", type="note")

    query_vec = embed(["python tabs indentation coding style"])[0]
    results = store.semantic_search(query_vec, limit=3)

    print("ranking for 'python tabs indentation coding style':")
    for r in results:
        print(f"  score={r['score']:.4f}  {r['content']}")

    assert results, "expected results"
    assert results[0]["content"].startswith("Prefers Python"), "most relevant item should rank first"
    assert results[0]["score"] > results[-1]["score"], "scores should differentiate"
    assert "embedding" not in results[0], "raw vectors must not leak to callers"

    print("\nOK — semantic ranking works and vectors stay internal.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
