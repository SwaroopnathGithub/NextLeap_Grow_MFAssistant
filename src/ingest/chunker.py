"""Phase 1b: Chunker.

Strategy (full rationale in data/chunks/chunking_notes.md):

The 10 sources are two different shapes of content:
  (a) Scheme pages: a dense run of short "label / value" lines rendered
      one per line by the page (Expense Ratio / 1.21 / Exit Load / NIL /
      Minimum SIP / Rs 500 / ...), followed by longer prose paragraphs
      (fund overview, description).
  (b) SIDs, SEBI pages, HDFC guides: mostly ordinary prose paragraphs,
      separated by blank lines.

So the chunker:
  1. Groups the text into runs: a contiguous run of SHORT lines (<= 10
     words, not ending in sentence punctuation) is kept together as ONE
     "key facts" block, since splitting a label from its value (or one
     fact from its neighbours) would break the very facts we need to
     retrieve. A run ends when a blank line or a long, sentence-like
     line appears.
  2. Ordinary prose is grouped by blank-line-delimited paragraphs.
  3. Any resulting block over MAX_CHUNK_CHARS is hard-split into
     fixed-size, overlapping windows (~300 tokens / ~1400 chars, ~15%
     overlap) so nothing is too large for the embedding model or the
     LLM's context window.
  4. Every chunk keeps metadata: source_id, source_url, scheme,
     source_type, fetched_at, and a best-effort field_hint (which of
     expense_ratio / exit_load / min_sip / lock_in / riskometer /
     benchmark / statement_howto keywords appear in it) - used for
     inspection/debugging, not for retrieval itself.

Chunks are written to data/chunks/chunks.txt in a readable format:
  ---
  id: <n>
  source_id: <id>
  source_url: <url>
  scheme: <scheme>
  field_hint: <hint>
  ---
  <chunk text>

Run directly: python -m src.ingest.chunker
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
MANIFEST_PATH = RAW_DIR / "manifest.json"
CHUNKS_DIR = REPO_ROOT / "data" / "chunks"
CHUNKS_TXT = CHUNKS_DIR / "chunks.txt"
CHUNKS_JSON = CHUNKS_DIR / "chunks.json"

MAX_CHUNK_CHARS = 1400  # ~300-350 tokens
OVERLAP_CHARS = 220  # ~15-20% of MAX_CHUNK_CHARS
SHORT_LINE_MAX_WORDS = 10

FIELD_KEYWORDS = {
    "expense_ratio": ["expense ratio", "ter", "total expense"],
    "exit_load": ["exit load"],
    "min_sip": ["minimum sip", "min sip", "min. sip"],
    "lock_in": ["lock-in", "lock in", "lockin"],
    "riskometer": ["riskometer", "risk-o-meter", "risk level"],
    "benchmark": ["benchmark"],
    "statement_howto": ["account statement", "capital gain", "consolidated account", "cas"],
}


@dataclass
class Chunk:
    id: int
    source_id: str
    source_url: str
    scheme: str
    source_type: str
    fetched_at: str
    field_hint: str
    text: str


def _keyword_present(keyword: str, lowered_text: str) -> bool:
    """Word-boundary match so short keywords like 'ter' don't false-positive
    inside unrelated words (e.g. 'Riskometer' contains 'ter')."""
    pattern = r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])"
    return re.search(pattern, lowered_text) is not None


def _guess_field_hint(text: str) -> str:
    lowered = text.lower()
    hits = [
        field
        for field, kws in FIELD_KEYWORDS.items()
        if any(_keyword_present(k, lowered) for k in kws)
    ]
    return ",".join(hits)


def _is_short_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.endswith((".", ";")):
        return False
    return len(stripped.split()) <= SHORT_LINE_MAX_WORDS


def _structural_blocks(text: str) -> list[str]:
    """Run-length group: contiguous short lines become one 'key facts'
    block; blank lines and long prose lines are paragraph boundaries."""
    lines = [l for l in text.split("\n")]
    blocks: list[list[str]] = []
    current: list[str] = []
    current_is_short_run = False

    def flush():
        nonlocal current
        if current:
            blocks.append(current)
            current = []

    for line in lines:
        if not line.strip():
            flush()
            continue
        short = _is_short_line(line)
        if not current:
            current = [line]
            current_is_short_run = short
        elif short == current_is_short_run:
            current.append(line)
        else:
            flush()
            current = [line]
            current_is_short_run = short
    flush()

    return ["\n".join(b).strip() for b in blocks if "\n".join(b).strip()]


def _fixed_window_split(text: str) -> list[str]:
    if len(text) <= MAX_CHUNK_CHARS:
        return [text]
    windows = []
    start = 0
    step = MAX_CHUNK_CHARS - OVERLAP_CHARS
    while start < len(text):
        windows.append(text[start : start + MAX_CHUNK_CHARS])
        start += step
    return windows


def chunk_text(text: str) -> list[str]:
    blocks = _structural_blocks(text)
    final: list[str] = []
    for block in blocks:
        final.extend(_fixed_window_split(block))
    return [b for b in final if b.strip()]


def run() -> list[Chunk]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    chunks: list[Chunk] = []
    next_id = 0

    for record in manifest:
        if record["status"] != "ok":
            continue
        raw_path = REPO_ROOT / record["raw_path"]
        text = raw_path.read_text(encoding="utf-8")
        for piece in chunk_text(text):
            chunks.append(
                Chunk(
                    id=next_id,
                    source_id=record["id"],
                    source_url=record["url"],
                    scheme=record["scheme"],
                    source_type=record["source_type"],
                    fetched_at=record["fetched_at"],
                    field_hint=_guess_field_hint(piece),
                    text=piece,
                )
            )
            next_id += 1

    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
    CHUNKS_JSON.write_text(
        json.dumps([asdict(c) for c in chunks], indent=2), encoding="utf-8"
    )

    with open(CHUNKS_TXT, "w", encoding="utf-8") as f:
        for c in chunks:
            f.write("---\n")
            f.write(f"id: {c.id}\n")
            f.write(f"source_id: {c.source_id}\n")
            f.write(f"source_url: {c.source_url}\n")
            f.write(f"scheme: {c.scheme}\n")
            f.write(f"field_hint: {c.field_hint}\n")
            f.write("---\n")
            f.write(c.text + "\n\n")

    print(f"Chunker: {len(chunks)} chunks written to {CHUNKS_TXT}")
    return chunks


if __name__ == "__main__":
    run()
