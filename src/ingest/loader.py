"""Phase 1a: Loader.

Reads sources.csv, fetches each source (HTML page or PDF), extracts clean
text, and writes one .txt file per source under data/raw/, plus a
manifest.json recording fetch status/metadata for every source.

Run directly: python -m src.ingest.loader
"""
from __future__ import annotations

import csv
import json
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCES_CSV = REPO_ROOT / "sources.csv"
RAW_DIR = REPO_ROOT / "data" / "raw"
MANIFEST_PATH = RAW_DIR / "manifest.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}
TIMEOUT_SECONDS = 30


@dataclass
class SourceRecord:
    id: str
    url: str
    source_type: str
    scheme: str
    covers: str
    status: str  # "ok" | "failed"
    fetched_at: str
    raw_path: str = ""
    error: str = ""


def _clean_html_to_text(html: str) -> str:
    """Strip nav/script/style/footer noise, keep the readable body text."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    # Collapse excess blank lines left by stripped tags.
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def _extract_pdf_text(content: bytes) -> str:
    import io

    reader = PdfReader(io.BytesIO(content))
    pages = []
    for i, page in enumerate(reader.pages):
        page_text = page.extract_text() or ""
        if page_text.strip():
            pages.append(f"[PDF page {i + 1}]\n{page_text.strip()}")
    return "\n\n".join(pages)


def fetch_one(row: dict) -> SourceRecord:
    source_id = row["id"]
    url = row["url"]
    fetched_at = datetime.now(timezone.utc).isoformat()
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if url.lower().endswith(".pdf") or "application/pdf" in content_type:
            text = _extract_pdf_text(resp.content)
        else:
            text = _clean_html_to_text(resp.text)

        if not text.strip():
            raise ValueError("extracted text was empty")

        raw_path = RAW_DIR / f"{source_id}.txt"
        raw_path.write_text(text, encoding="utf-8")
        return SourceRecord(
            id=source_id,
            url=url,
            source_type=row.get("source_type", ""),
            scheme=row.get("scheme", ""),
            covers=row.get("covers", ""),
            status="ok",
            fetched_at=fetched_at,
            raw_path=str(raw_path.relative_to(REPO_ROOT)),
        )
    except Exception as exc:  # noqa: BLE001 - we want to record *any* failure and continue
        return SourceRecord(
            id=source_id,
            url=url,
            source_type=row.get("source_type", ""),
            scheme=row.get("scheme", ""),
            covers=row.get("covers", ""),
            status="failed",
            fetched_at=fetched_at,
            error=str(exc),
        )


def run() -> list[SourceRecord]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with open(SOURCES_CSV, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r.get("id")]

    records = [fetch_one(row) for row in rows]

    MANIFEST_PATH.write_text(
        json.dumps([asdict(r) for r in records], indent=2), encoding="utf-8"
    )

    ok = sum(1 for r in records if r.status == "ok")
    failed = [r for r in records if r.status == "failed"]
    print(f"Loader: {ok}/{len(records)} sources fetched successfully.")
    for r in failed:
        print(f"  FAILED [{r.id}] {r.url} -> {r.error}", file=sys.stderr)
    return records


if __name__ == "__main__":
    run()
