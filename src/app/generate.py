"""Phase 5: LLM answer generation.

Builds the system prompt (answer only from provided chunks; <=3 sentences;
cite exactly one source URL from the top chunk; append "Last updated from
sources: <date>"), calls Groq with the question + retrieved chunks +
recent conversation memory, and returns the formatted answer.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass

from src.app.retriever import RetrievedChunk

_CITED_INDEX_RE = re.compile(r"\n?CITED_INDEX:\s*(\d+)\s*$", re.IGNORECASE)

SYSTEM_PROMPT = """You are a facts-only assistant for HDFC Mutual Fund schemes (Groww's \
reference product). You answer ONLY using the "Retrieved context" chunks given to you in \
each turn - never from general knowledge, never by guessing or estimating a number. Each \
context chunk is labelled with a bracketed index like [1], [2], plus its scheme, \
source_url, and fetched_at date.

Rules, no exceptions:
1. Use only facts present in the retrieved context below. If the context does not contain \
the answer, or is about a different scheme than the one asked about, say plainly that you \
don't have that in your sources - do not guess, estimate, or use outside knowledge.
2. Never state a numeric value (a ratio, an amount, a lock-in period, a percentage) unless \
that exact value appears in the retrieved context.
3. Keep the answer to 3 sentences or fewer, in plain prose - no Markdown links, no bracket \
citation markers, no footnotes inside the answer text itself.
4. "Source" means source_url, not an individual numbered chunk - several retrieved chunks \
often come from the same source_url (the same scheme page can supply several small facts, \
e.g. one chunk for riskometer and another for benchmark). Freely combine facts from \
DIFFERENT chunks as long as they share the same source_url. Only if the facts you need span \
chunks with genuinely different source_urls should you pick the single most relevant \
source_url and answer only what that one source_url supports.
5. Never give investment advice, performance comparisons, or opinions - you only relay \
documented facts from the 10-source corpus you were given.
6. End your reply with exactly two more lines, in this order, and nothing after them:
   Last updated from sources: <fetched_at date of the chunk you cited>
   CITED_INDEX: <the bracket number, e.g. 1, of the chunk whose source_url your answer is \
based on - if you used several chunks that share one source_url, give any one of their \
numbers>
If you don't have the answer in your sources, skip both of those last two lines entirely."""

DEFAULT_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

NO_MATCH_MESSAGE = (
    "I don't have that in my sources. I can only answer questions about the expense ratio, "
    "exit load, minimum SIP, ELSS lock-in, riskometer, benchmark, or statement downloads for "
    "HDFC Large Cap, Flexi Cap, ELSS Tax Saver, and Mid Cap funds."
)


@dataclass
class Turn:
    question: str
    answer: str


@dataclass
class GenerationResult:
    text: str  # display text, with the CITED_INDEX marker line stripped
    citation_url: str | None


def _format_context(chunks: list[RetrievedChunk]) -> str:
    parts = []
    for i, c in enumerate(chunks, start=1):
        fetched_date = c.fetched_at.split("T")[0] if "T" in c.fetched_at else c.fetched_at
        parts.append(
            f"[{i}] scheme={c.scheme} source_url={c.source_url} fetched_at={fetched_date}\n{c.text}"
        )
    return "\n\n".join(parts)


def _format_memory(memory: list[Turn]) -> str:
    if not memory:
        return ""
    lines = []
    for turn in memory[-10:]:
        lines.append(f"User: {turn.question}\nAssistant: {turn.answer}")
    return "\n\n".join(lines)


def _get_client():
    from groq import Groq

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your key "
            "(https://console.groq.com/keys)."
        )
    return Groq(api_key=api_key)


def generate_answer(
    question: str,
    chunks: list[RetrievedChunk],
    memory: list[Turn] | None = None,
    model: str = DEFAULT_MODEL,
) -> GenerationResult:
    memory = memory or []
    context = _format_context(chunks)
    memory_block = _format_memory(memory)

    user_content = ""
    if memory_block:
        user_content += f"Recent conversation:\n{memory_block}\n\n"
    user_content += f"Retrieved context:\n{context}\n\nQuestion: {question}"

    client = _get_client()
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        temperature=0.1,
        max_tokens=800,
        reasoning_effort="low",
    )
    raw = completion.choices[0].message.content.strip()

    match = _CITED_INDEX_RE.search(raw)
    citation_url = None
    if match:
        idx = int(match.group(1))
        if 1 <= idx <= len(chunks):
            citation_url = chunks[idx - 1].source_url
        raw = _CITED_INDEX_RE.sub("", raw).rstrip()

    return GenerationResult(text=raw, citation_url=citation_url)
