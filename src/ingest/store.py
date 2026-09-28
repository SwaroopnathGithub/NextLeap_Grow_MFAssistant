"""Phase 2b: Vector store.

ChromaDB client persisted to data/chroma/, with a single collection
(mf_faq_chunks). rebuild_from_chunks() clears and re-adds so ingestion is
idempotent: running it twice in a row yields the same chunk count.
"""
from __future__ import annotations

import json
from pathlib import Path

import chromadb

from src.ingest.embedder import embed_texts

REPO_ROOT = Path(__file__).resolve().parents[2]
CHROMA_DIR = REPO_ROOT / "data" / "chroma"
CHUNKS_JSON = REPO_ROOT / "data" / "chunks" / "chunks.json"
COLLECTION_NAME = "mf_faq_chunks"

_BATCH_SIZE = 100


def get_client() -> chromadb.ClientAPI:
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def get_collection(client: chromadb.ClientAPI | None = None):
    client = client or get_client()
    return client.get_or_create_collection(COLLECTION_NAME)


def rebuild_from_chunks(chunks_path: Path = CHUNKS_JSON) -> int:
    """Clear the collection and re-add every chunk from chunks.json.
    Returns the number of chunks stored."""
    chunks = json.loads(chunks_path.read_text(encoding="utf-8"))

    client = get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )

    for i in range(0, len(chunks), _BATCH_SIZE):
        batch = chunks[i : i + _BATCH_SIZE]
        ids = [str(c["id"]) for c in batch]
        documents = [c["text"] for c in batch]
        embeddings = embed_texts(documents)
        metadatas = [
            {
                "source_id": c["source_id"],
                "source_url": c["source_url"],
                "scheme": c["scheme"],
                "source_type": c["source_type"],
                "fetched_at": c["fetched_at"],
                "field_hint": c["field_hint"],
            }
            for c in batch
        ]
        collection.add(ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas)

    return len(chunks)


def query(question_embedding: list[float], top_k: int = 4) -> dict:
    collection = get_collection()
    return collection.query(query_embeddings=[question_embedding], n_results=top_k)
