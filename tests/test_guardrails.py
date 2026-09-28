"""Unit tests for the guardrail classifier: ~15 sample questions covering
factual, PII, advice, and performance buckets, with expected outcomes.

Run: python -m pytest tests/test_guardrails.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.app.guardrails import check  # noqa: E402

CASES = [
    # (question, expected_outcome, expected_reason_or_None)
    ("What is the expense ratio of HDFC ELSS Tax Saver?", "FACTUAL", None),
    ("What is the minimum SIP amount for HDFC Large Cap Fund?", "FACTUAL", None),
    ("What is the lock-in period for HDFC ELSS Tax Saver?", "FACTUAL", None),
    ("What is the exit load on HDFC Flexi Cap Fund?", "FACTUAL", None),
    ("What is the riskometer level and benchmark for HDFC Mid Cap Fund?", "FACTUAL", None),
    ("How do I download my capital gains statement?", "FACTUAL", None),
    ("How do I download a consolidated account statement?", "FACTUAL", None),
    ("Should I invest in HDFC ELSS or HDFC Flexi Cap?", "REFUSE", "advice"),
    ("Which HDFC fund gave the best returns last year?", "REFUSE", "performance"),
    ("Is now a good time to buy HDFC Mid Cap Fund?", "REFUSE", "advice"),
    ("My PAN is ABCDE1234F, can you check my portfolio?", "REFUSE", "pii"),
    ("My email is investor@example.com, please send my statement there.", "REFUSE", "pii"),
    ("My Aadhaar number is 1234 5678 9012, can you verify me?", "REFUSE", "pii"),
    ("Which fund would you recommend for a 5 year horizon?", "REFUSE", "advice"),
    ("Can you compare the performance of Large Cap vs Mid Cap?", "REFUSE", "performance"),
]


def test_guardrail_cases():
    failures = []
    for question, expected_outcome, expected_reason in CASES:
        result = check(question)
        if result.outcome != expected_outcome or (
            expected_reason and result.reason != expected_reason
        ):
            failures.append(
                f"Q: {question!r} -> got outcome={result.outcome} reason={result.reason!r}, "
                f"expected outcome={expected_outcome} reason={expected_reason!r}"
            )
    assert not failures, "\n" + "\n".join(failures)


if __name__ == "__main__":
    test_guardrail_cases()
    print(f"All {len(CASES)} guardrail cases passed.")
