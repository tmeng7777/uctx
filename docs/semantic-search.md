# Semantic search (branch: `semantic-search`)

Upgrades `search_context` from substring matching to embedding-based similarity,
so "what are my coding preferences?" finds "Prefers Python, tabs over spaces"
even with no shared keywords.

## Design: bring your own embedder

Vendor-neutral by design (that's uctx's whole point). Pick a backend with
`$UCTX_EMBEDDER`:

| value | needs | notes |
|-------|-------|-------|
| `keyword` / unset | nothing | **default** — substring search, unchanged from main |
| `stub` | nothing | deterministic bag-of-words hash; for tests / offline dev |
| `openai` | `pip install "uctx[openai]"` + `OPENAI_API_KEY` | real semantic matching |
| `gemini` | `pip install "uctx[gemini]"` + `GOOGLE_API_KEY` | real semantic matching |

- Embeddings are computed on `save_context` and stored in a nullable `embedding`
  column (JSON) — old rows and keyword mode leave it `NULL`.
- `search_context` uses cosine similarity when an embedder is configured, and
  falls back to substring search otherwise. Raw vectors never leave the store.

## Try it

```bash
# offline, no key:
UCTX_EMBEDDER=stub uv run python tests/semantic_test.py

# real semantics:
uv sync --extra openai
UCTX_EMBEDDER=openai OPENAI_API_KEY=sk-... uv run uctx
```

## Status / open questions

- The `stub` embedder proves the plumbing (storage, cosine ranking, fallback),
  not synonym matching — that needs a real provider.
- Next: batch-embed on backfill for existing rows; consider `sqlite-vec` for
  fast ANN instead of scanning all rows in Python.
