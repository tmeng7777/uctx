"""Pluggable embeddings — bring your own embedder.

Vendor-neutral on purpose: uctx's whole thesis is that you shouldn't be locked
to one provider, so the embedder is swappable via $UCTX_EMBEDDER:

    keyword | none  -> no embedder (fall back to substring search)  [default]
    stub            -> deterministic, dependency-free (for tests / offline dev)
    openai          -> OpenAI embeddings   (pip install "uctx[openai]")
    gemini          -> Gemini embeddings   (pip install "uctx[gemini]")

Only `stub` and `keyword` need zero setup. `stub` is a bag-of-words hash, NOT a
real semantic model — it's for tests. Real synonym/semantic matching comes from
the openai/gemini providers.
"""

from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Callable

Embedder = Callable[[list[str]], list[list[float]]]

_STUB_DIMS = 128


def get_embedder() -> Embedder | None:
    name = os.environ.get("UCTX_EMBEDDER", "").strip().lower()
    if name in ("", "keyword", "none"):
        return None
    if name == "stub":
        return _stub_embed
    if name == "openai":
        return _openai_embedder()
    if name == "gemini":
        return _gemini_embedder()
    raise ValueError(f"Unknown UCTX_EMBEDDER={name!r} (use keyword|stub|openai|gemini)")


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)


# --- providers ---------------------------------------------------------------
def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _stub_embed(texts: list[str]) -> list[list[float]]:
    """Deterministic bag-of-words hashing embedding (no dependencies)."""
    out = []
    for text in texts:
        vec = [0.0] * _STUB_DIMS
        for tok in _tokens(text):
            h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
            vec[h % _STUB_DIMS] += 1.0
        out.append(vec)
    return out


def _openai_embedder() -> Embedder:
    from openai import OpenAI  # optional dependency

    client = OpenAI()
    model = os.environ.get("UCTX_OPENAI_EMBED_MODEL", "text-embedding-3-small")

    def embed(texts: list[str]) -> list[list[float]]:
        resp = client.embeddings.create(model=model, input=texts)
        return [d.embedding for d in resp.data]

    return embed


def _gemini_embedder() -> Embedder:
    from google import genai  # optional dependency

    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    model = os.environ.get("UCTX_GEMINI_EMBED_MODEL", "text-embedding-004")

    def embed(texts: list[str]) -> list[list[float]]:
        resp = client.models.embed_content(model=model, contents=texts)
        return [list(e.values) for e in resp.embeddings]

    return embed
