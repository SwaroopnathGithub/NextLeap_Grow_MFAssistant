# Chunking strategy notes

Written after inspecting the shape of the 10 sources (via earlier live checks
of the HDFC scheme pages, the SEBI pages, and the HDFC guide pages) and
before writing `chunker.py`.

## What the data looks like
Two shapes:
1. **Scheme pages** (4 HDFC fund pages): a dense run of short label/value
   lines - "Expense Ratio (TER)" / "1.21" / "Exit Load" / "NIL" / ... -
   followed by a longer prose "Fund Overview" section.
2. **Everything else** (2 SIDs, HDFC statement page, HDFC capital-gains
   guide, 2 SEBI pages): ordinary prose, paragraph by paragraph.

## Why a single fixed-size splitter would hurt this data
A single fixed-size window (e.g. "every 300 tokens") risks slicing a label
from its value on the scheme pages (e.g. "Expense Ratio (TER)" ending one
chunk, "1.21" starting the next) - which would break exactly the facts this
assistant needs to retrieve and cite.

## Strategy chosen
1. **Run-length grouping first:** walk the text line by line. A run of
   consecutive "short" lines (≤10 words, not ending in `.`/`;`) is kept
   together as one block, since that's how a label and its value appear on
   the scheme pages. A blank line, or a line that reads as a full sentence
   (long / ends in punctuation), ends the run and starts a new block.
   This keeps every label with its value, and keeps ordinary paragraphs
   as their own blocks.
2. **Fixed-size fallback:** any block still over ~1400 characters
   (~300-350 tokens) is hard-split into overlapping windows (~1400 chars,
   ~220 char / ~15-20% overlap), so nothing overflows the embedding model
   or the LLM's context - this only fires on the longer prose blocks
   (SID text, SEBI circular text), never on the short scheme-page facts.
3. **Metadata kept per chunk:** `source_id`, `source_url`, `scheme`,
   `source_type`, `fetched_at`, and a best-effort `field_hint` (regex,
   word-boundary matched, so short keywords like "TER" don't false-hit
   inside unrelated words such as "Riskometer"). `field_hint` is for
   human inspection/debugging only - retrieval itself uses the embedding,
   not this hint.

## Validated with unit tests (`tests/test_chunker.py`)
Against a synthetic fixture shaped exactly like a real HDFC scheme page:
- Every fact (expense ratio, exit load, min SIP, lock-in, riskometer,
  benchmark) lands in its own correctly-hinted chunk.
- A label and its value never get separated into different chunks.
- The "Riskometer" / "TER" false-positive case is specifically tested and
  passes.
- A long, blank-line-free prose block correctly falls back to fixed-size
  overlapping windows.

## Update: validated against the real fetched sources (2026-09-28)
All 10 sources were fetched from a local machine (browser pane for the
HTML pages that block direct HTTP requests; direct `curl` for the 2 SID
PDFs and the SEBI TER circular PDF) and run through the real pipeline.

**PDF extraction fix required:** `pypdf`'s raw `page.extract_text()`
returns one line per *visual* line in the PDF layout, not per sentence.
Feeding that directly into the structural chunker produced ~1040 tiny
chunks per 74-page SID (avg 180 chars, many just a page number or a
2-3 word label) because nearly every PDF line looked like a "short
line" and was separated from its neighbours by blank lines. Fixed by
adding a line-joining pass before chunking: consecutive PDF lines are
merged into a paragraph unless the previous line ends in `.`/`:`/`;`
or the next line starts with a bullet/number marker. This dropped the
two SIDs from ~1040 chunks each to ~433/432 (avg chunk length 377
chars), which now read as real paragraphs/fact-blocks instead of
single-line fragments.

**Final counts by source (1259 chunks total):** the 4 scheme pages
(64-91 chunks each) chunk cleanly into their key-facts blocks; the two
SIDs (~433 each) now read as proper paragraphs; the remaining sources
(HDFC statement page, capital-gains guide, SEBI riskometer, SEBI TER
circular) are 10-44 chunks each of ordinary prose. Spot-checked
manually against the checklist above (facts not merged, labels stay
with values, no TER/Riskometer false-positive) — passes.
