"""Phase 4: Retriever.

Embeds an already-guardrail-cleared question with the same MiniLM model
used at ingestion, queries ChromaDB for top-k chunks, and short-circuits to
NO_MATCH when the best hit is too weak - so the caller never hands the LLM
a context it has to guess from.

ChromaDB distances here are cosine distance (0 = identical, 2 = opposite;
see src/ingest/store.py's "hnsw:space": "cosine"), so lower is better and
a same-topic "<scheme> — <label>: <value>" chunk typically lands at
0.10-0.25 against a matching factual question (measured against this
project's real corpus - see retrieval spot checks in the session that
built this). NO_MATCH_DISTANCE_THRESHOLD is set above that working range
so genuinely unrelated questions (asking about a scheme/fact not in the
10-source corpus) are rejected instead of forcing a weak guess.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.ingest.embedder import embed_query
from src.ingest.store import get_collection

DEFAULT_TOP_K = 4
NO_MATCH_DISTANCE_THRESHOLD = 0.55


@dataclass
class RetrievedChunk:
    text: str
    source_url: str
    scheme: str
    source_type: str
    fetched_at: str
    distance: float


@dataclass
class RetrievalResult:
    outcome: str  # "OK" | "NO_MATCH"
    chunks: list[RetrievedChunk]


def retrieve(question: str, top_k: int = DEFAULT_TOP_K) -> RetrievalResult:
    embedding = embed_query(question)
    collection = get_collection()
    res = collection.query(query_embeddings=[embedding], n_results=top_k)

    documents = res["documents"][0]
    distances = res["distances"][0]
    metadatas = res["metadatas"][0]

    if not documents or distances[0] > NO_MATCH_DISTANCE_THRESHOLD:
        return RetrievalResult(outcome="NO_MATCH", chunks=[])

    chunks = [
        RetrievedChunk(
            text=doc,
            source_url=meta["source_url"],
            scheme=meta["scheme"],
            source_type=meta["source_type"],
            fetched_at=meta["fetched_at"],
            distance=dist,
        )
        for doc, dist, meta in zip(documents, distances, metadatas)
    ]
    return RetrievalResult(outcome="OK", chunks=chunks)
