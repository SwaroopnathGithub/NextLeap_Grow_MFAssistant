"""Ingestion entrypoint: Loader -> Chunker -> Embed & Store, end to end.

Run: python -m src.ingest.run

Note: hdfcfund.com and investor.sebi.gov.in sit behind Akamai bot
protection that returns 403 to loader.py's plain `requests` fetch (this is
a bot-detection block, not a network/firewall block - it 403s from any
plain HTTP client, including on an unrestricted machine). Those 6 of the
10 sources were fetched once via a real browser and committed under
data/raw/ (see data/raw/manifest.json for method/status per source). So
this entrypoint skips the network fetch when data/raw/manifest.json
already shows all 10 sources as "ok", and only re-fetches if it's missing
or incomplete - keeping ingestion (and Render's build-time rebuild)
reliable without depending on bypassing that bot protection at build time.
"""
from __future__ import annotations

import json

from src.ingest import chunker, loader, store

MANIFEST_PATH = loader.MANIFEST_PATH


def _raw_data_is_complete() -> bool:
    if not MANIFEST_PATH.exists():
        return False
    try:
        records = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False
    if len(records) != 10:
        return False
    return all(r.get("status") == "ok" for r in records)


def run() -> None:
    if _raw_data_is_complete():
        print("Loader: data/raw/manifest.json already has all 10 sources marked ok - skipping fetch.")
    else:
        loader.run()
    chunker.run()
    count = store.rebuild_from_chunks()
    print(f"Store: {count} chunks embedded and persisted to data/chroma/")


if __name__ == "__main__":
    run()
