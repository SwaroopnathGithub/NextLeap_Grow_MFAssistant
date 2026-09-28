"""Phase 3: Guardrails.

Three independent, deterministic checks run on the raw user question,
before any retrieval or LLM call. Cheap and predictable: refusals never
touch the LLM or ChromaDB, and PII input is never logged verbatim.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

SEBI_RISKOMETER_URL = "https://investor.sebi.gov.in/riskometer.html"
FACTSHEET_URL = "https://www.hdfcfund.com/explore/mutual-funds"
FACTSHEET_HINT = f"the relevant scheme's official page on hdfcfund.com ({FACTSHEET_URL}) - see Downloads > SID / Fund Facts"

PII_PATTERNS = [
    ("PAN", re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)),
    ("Aadhaar", re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b")),
    ("phone", re.compile(r"\b(?:\+?91[-\s]?)?[6-9]\d{9}\b")),
]
OTP_NEAR_TRIGGER = re.compile(r"\botp\b.{0,20}\b\d{4,6}\b|\b\d{4,6}\b.{0,20}\botp\b", re.IGNORECASE)

ADVICE_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"should i (buy|sell|invest|switch)",
        r"buy or sell",
        r"which (is|one is|fund is) better",
        r"\brecommend(ed|ation)?\b",
        r"worth investing",
        r"good (time|idea) to (invest|buy|sell)",
        r"what should i do",
    ]
]

PERFORMANCE_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\breturns?\b",
        r"\bperformance\b",
        r"\bcompare\b|\bcomparison\b",
        r"outperform",
        r"gave (the )?(best|most|highest)",
        r"which fund (gave|did) (more|better)",
    ]
]


@dataclass
class GuardrailResult:
    outcome: str  # "FACTUAL" | "REFUSE"
    reason: str = ""
    link: str = ""
    message: str = ""


def _check_pii(question: str) -> GuardrailResult | None:
    for _label, pattern in PII_PATTERNS:
        if pattern.search(question):
            return GuardrailResult(
                outcome="REFUSE",
                reason="pii",
                message=(
                    "I can't accept or process personal information (PAN, Aadhaar, phone, "
                    "email, or similar identifiers) - please don't share that here."
                ),
            )
    if OTP_NEAR_TRIGGER.search(question):
        return GuardrailResult(
            outcome="REFUSE",
            reason="pii",
            message=(
                "I can't accept or process personal information (PAN, Aadhaar, phone, "
                "email, or similar identifiers) - please don't share that here."
            ),
        )
    return None


def _check_advice(question: str) -> GuardrailResult | None:
    if any(p.search(question) for p in ADVICE_PATTERNS):
        return GuardrailResult(
            outcome="REFUSE",
            reason="advice",
            link=SEBI_RISKOMETER_URL,
            message=(
                "I can't give investment advice or recommendations. For help matching a "
                f"scheme's risk level to your own risk appetite, see SEBI's riskometer guide: {SEBI_RISKOMETER_URL}"
            ),
        )
    return None


def _check_performance(question: str) -> GuardrailResult | None:
    if any(p.search(question) for p in PERFORMANCE_PATTERNS):
        return GuardrailResult(
            outcome="REFUSE",
            reason="performance",
            link=FACTSHEET_URL,
            message=(
                "I don't compute or compare fund returns or performance. For official "
                f"performance figures, check {FACTSHEET_HINT}."
            ),
        )
    return None


def check(question: str) -> GuardrailResult:
    """Run all three checks in order (PII first). The first match wins;
    anything unmatched is treated as factual and proceeds to retrieval."""
    for check_fn in (_check_pii, _check_advice, _check_performance):
        result = check_fn(question)
        if result is not None:
            return result
    return GuardrailResult(outcome="FACTUAL")
