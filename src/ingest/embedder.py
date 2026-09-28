"""Phase 2a: Embedder.

Loads sentence-transformers/all-MiniLM-L6-v2 once and exposes embedding
functions shared by ingestion (embed many chunks) and query time (embed one
question), so both live in the same vector space.
"""
from __future__ import annotations

from functools import lru_cache

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _get_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of chunk texts (used at ingestion)."""
    model = _get_model()
    return model.encode(list(texts), show_progress_bar=False).tolist()


def embed_query(text: str) -> list[float]:
    """Embed a single question (used at query time). Same code path/model
    instance as embed_texts so query and chunk vectors share a space."""
    model = _get_model()
    return model.encode([text], show_progress_bar=False)[0].tolist()
