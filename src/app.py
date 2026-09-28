"""Phase 6: Streamlit UI.

Welcome line, 3 clickable example questions, a fixed disclaimer, chat
input/output wired through answer_question(), citation rendered as a
clickable link. No PII-inviting form fields anywhere.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import streamlit as st  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

load_dotenv(REPO_ROOT / ".env")

from src.app.generate import Turn  # noqa: E402
from src.app.pipeline import answer_question  # noqa: E402

DISCLAIMER = "Facts-only. No investment advice."

EXAMPLE_QUESTIONS = [
    "What is the expense ratio of HDFC ELSS Tax Saver?",
    "What is the lock-in period for HDFC ELSS Tax Saver?",
    "How do I download my capital gains statement?",
]

st.set_page_config(page_title="Groww MF Facts-Only Assistant", page_icon="\U0001F4CA")

st.title("Groww MF Facts-Only Assistant")
st.caption(
    "Ask a factual question about HDFC Large Cap, Flexi Cap, ELSS Tax Saver, or Mid Cap Fund "
    "(expense ratio, exit load, minimum SIP, ELSS lock-in, riskometer, benchmark, or how to "
    "download a statement). Every factual answer cites exactly one official source."
)
st.warning(DISCLAIMER, icon="⚠️")

if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {"role": ..., "content": ..., "citation": ...}
if "memory" not in st.session_state:
    st.session_state.memory: list[Turn] = []

st.markdown("**Try an example:**")
example_cols = st.columns(len(EXAMPLE_QUESTIONS))
example_clicked = None
for col, q in zip(example_cols, EXAMPLE_QUESTIONS):
    if col.button(q, use_container_width=True):
        example_clicked = q

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("citation"):
            st.markdown(f"[Source]({msg['citation']})")

user_input = st.chat_input("Ask about an HDFC scheme's facts...")
question = example_clicked or user_input

if question:
    with st.chat_message("user"):
        st.markdown(question)
    st.session_state.messages.append({"role": "user", "content": question, "citation": None})

    with st.chat_message("assistant"):
        with st.spinner("Looking that up..."):
            result = answer_question(question, memory=st.session_state.memory)
        st.markdown(result.answer)
        if result.citation_url:
            st.markdown(f"[Source]({result.citation_url})")

    st.session_state.messages.append(
        {"role": "assistant", "content": result.answer, "citation": result.citation_url}
    )
    if not result.refused:
        st.session_state.memory.append(Turn(question=question, answer=result.answer))
        st.session_state.memory = st.session_state.memory[-10:]

    if example_clicked:
        st.rerun()
