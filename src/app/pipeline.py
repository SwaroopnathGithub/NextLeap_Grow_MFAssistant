"""Wires guardrails (Phase 3) -> retriever (Phase 4) -> generation (Phase
5) into the single orchestrator used by the UI: answer_question().

Conversation memory (last 10 turns) is kept by the caller (the UI) and
passed in on every call; the guardrail check always runs fresh on the new
message and is never bypassed by memory.
"""
from __future__ import annotations

from dataclasses import dataclass

from src.app import guardrails
from src.app.generate import NO_MATCH_MESSAGE, Turn, generate_answer
from src.app.retriever import RetrievalResult, retrieve


@dataclass
class AnswerResult:
    answer: str
    citation_url: str | None
    refused: bool
    refusal_reason: str | None = None


def answer_question(
    question: str,
    memory: list[Turn] | None = None,
) -> AnswerResult:
    memory = memory or []

    guard = guardrails.check(question)
    if guard.outcome == "REFUSE":
        return AnswerResult(
            answer=guard.message,
            citation_url=guard.link or None,
            refused=True,
            refusal_reason=guard.reason,
        )

    retrieval: RetrievalResult = retrieve(question)
    if retrieval.outcome == "NO_MATCH":
        return AnswerResult(answer=NO_MATCH_MESSAGE, citation_url=None, refused=False)

    generation = generate_answer(question, retrieval.chunks, memory=memory)
    citation_url = generation.citation_url or retrieval.chunks[0].source_url

    return AnswerResult(answer=generation.text, citation_url=citation_url, refused=False)
