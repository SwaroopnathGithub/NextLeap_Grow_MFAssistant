"""Unit tests for the chunker, run against a synthetic fixture shaped like
the REAL fetched HDFC scheme pages: every label and value on its own line,
separated by a blank line (confirmed by inspecting the real fetched
data/raw/*.txt - see the "Update: validated against the real fetched
sources" note in data/chunks/chunking_notes.md), plus a longer prose
paragraph.

Run: python -m pytest tests/test_chunker.py -q
(or: python -m tests.test_chunker  to run without pytest)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.ingest.chunker import chunk_text, _guess_field_hint  # noqa: E402

SCHEME_NAME = "HDFC ELSS Tax Saver"

SAMPLE_SCHEME_PAGE = """HDFC ELSS Tax Saver - Direct Plan

TER

1.21

Exit Load

NIL

Min SIP

Rs 500

Lock in

3 years

Riskometer

Very High

Benchmark

NIFTY 500 Total Returns Index

Fund Overview
This is an open ended equity linked savings scheme with a statutory lock in of 3 years and tax benefit.
The scheme aims for long-term capital appreciation through a diversified portfolio predominantly in equity and equity related instruments.
"""


def test_facts_are_not_merged_across_fields():
    chunks = chunk_text(SAMPLE_SCHEME_PAGE, scheme=SCHEME_NAME)
    hints = [_guess_field_hint(c) for c in chunks]
    for expected in ["expense_ratio", "exit_load", "min_sip", "lock_in", "riskometer", "benchmark"]:
        assert expected in hints, f"expected a chunk hinting at {expected}, got hints={hints}"


def test_expense_ratio_value_stays_with_its_label():
    chunks = chunk_text(SAMPLE_SCHEME_PAGE, scheme=SCHEME_NAME)
    ratio_chunk = next(c for c in chunks if _guess_field_hint(c) == "expense_ratio")
    assert "1.21" in ratio_chunk
    assert "TER" in ratio_chunk


def test_riskometer_keyword_does_not_false_positive_on_expense_ratio():
    # "Riskometer" contains the substring "ter" - must not be misread as
    # an expense-ratio ("TER") hit.
    chunks = chunk_text(SAMPLE_SCHEME_PAGE, scheme=SCHEME_NAME)
    risk_chunk = next(c for c in chunks if "Riskometer" in c and "Very High" in c)
    assert _guess_field_hint(risk_chunk) == "riskometer"


def test_key_fact_micro_chunks_pair_label_with_value_and_scheme():
    # Real scheme-page label/value blocks are diluted across many facts
    # once merged into one "key facts" block, which hurts embedding
    # similarity to a single-fact question - so each known field also gets
    # its own compact "<scheme> — <label>: <value>" chunk.
    chunks = chunk_text(SAMPLE_SCHEME_PAGE, scheme=SCHEME_NAME)
    assert f"{SCHEME_NAME} — TER (Expense Ratio): 1.21" in chunks
    assert f"{SCHEME_NAME} — Lock-in: 3 years" in chunks
    assert f"{SCHEME_NAME} — Riskometer: Very High" in chunks


def test_long_chunks_are_split_with_overlap():
    long_prose = "This is a long sentence about the fund. " * 100
    chunks = chunk_text(long_prose)
    assert len(chunks) > 1
    from src.ingest.chunker import MAX_CHUNK_CHARS

    assert all(len(c) <= MAX_CHUNK_CHARS for c in chunks)


if __name__ == "__main__":
    test_facts_are_not_merged_across_fields()
    test_expense_ratio_value_stays_with_its_label()
    test_riskometer_keyword_does_not_false_positive_on_expense_ratio()
    test_key_fact_micro_chunks_pair_label_with_value_and_scheme()
    test_long_chunks_are_split_with_overlap()
    print("All chunker tests passed.")
