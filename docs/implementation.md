# Implementation plan: Facts-Only Mutual Fund FAQ Assistant

Phased build plan, derived from PRD.md and architecture.md. Matches the phase numbering from Swaroop's NextLeap Buildhour session (Load & Chunk → Embed & Store → Guardrails → Retrieval → UI), with an added Phase 0 for scaffolding and a Phase 7 for submission packaging.

Each phase has: what gets built, the files touched, and a done-when check, so a phase is only marked complete once its check passes.

## Phase 0 — Project scaffolding
**Build:**
- Repo structure per architecture.md (`src/ingest/`, `src/app/`, `data/`, root files).
- `requirements.txt` (streamlit, chromadb, sentence-transformers, groq, python-dotenv, pypdf or similar for PDF text, requests/beautifulsoup4 for HTML fetch).
- `.env.example` with `GROQ_API_KEY=` and `GROQ_MODEL=openai/gpt-oss-120b`.
- `.gitignore` excluding `.env`, `data/chroma/`, `__pycache__/`.
- Copy `sources.csv` (the 10-source list) into the repo root.

**Files:** `requirements.txt`, `.env.example`, `.gitignore`, `sources.csv`, empty module stubs under `src/`.

**Done when:** repo scaffold exists, `pip install -r requirements.txt` succeeds locally.

## Phase 1 — Load & Chunk
**Build:**
- `src/ingest/loader.py`: fetch each of the 10 sources (HTML pages via requests + text extraction; the 2 SID PDFs via a PDF text extractor), write clean text to `data/raw/<id>.txt`, and `data/raw/manifest.json` with fetch metadata and status per source.
- `src/ingest/chunker.py`: inspect the fetched raw text first, then implement the chunking strategy decided in architecture.md (structural/heading split with fixed-size fallback, ~200–400 tokens, ~15–20% overlap). Write reasoning to `data/chunks/chunking_notes.md`. Attach metadata (`source_id`, `source_url`, `scheme_name`, `field_hint`, `fetched_at`) to every chunk.
- Save all chunks to `data/chunks/chunks.txt` in a human-readable format for manual inspection.

**Files:** `src/ingest/loader.py`, `src/ingest/chunker.py`, `data/raw/*`, `data/chunks/chunks.txt`, `data/chunks/chunking_notes.md`.

**Done when:** `data/chunks/chunks.txt` exists and, read manually, every scheme fact from the PRD (expense ratio, exit load, min SIP, lock-in, riskometer, benchmark, statement how-to) is visibly present in at least one chunk, correctly attributed to its source URL.

## Phase 2 — Embed & Store
**Build:**
- `src/ingest/embedder.py`: load `sentence-transformers/all-MiniLM-L6-v2` once; function to embed a list of chunk texts (used at ingestion) and a single string (used at query time), sharing the same code path so both stay in the same vector space.
- `src/ingest/store.py`: ChromaDB client persisted to `data/chroma/`; a `mf_faq_chunks` collection; a function to rebuild the collection from `data/chunks/chunks.txt` idempotently (clear then re-add).
- `src/ingest/run.py`: orchestrates Phase 1 + Phase 2 end to end as the single ingestion entrypoint (`python -m src.ingest.run`).

**Files:** `src/ingest/embedder.py`, `src/ingest/store.py`, `src/ingest/run.py`, `data/chroma/` (generated, gitignored).

**Done when:** running `python -m src.ingest.run` twice in a row produces the same chunk count in ChromaDB both times (idempotent), and `data/chroma/` persists across process restarts without rerunning ingestion.

## Phase 3 — Guardrails
**Build:**
- `src/app/guardrails.py`: three independent checks run in order on the raw user question, before any retrieval or LLM call —
  1. PII detector (regex: PAN format, Aadhaar format, email, phone, OTP-style digit codes near trigger words).
  2. Advice/opinion detector (keyword + pattern match: "should I", "buy or sell", "which is better", "recommend", "worth investing").
  3. Performance/comparison detector ("returns", "performance", "compare", "outperform").
- Each check returns a typed result: `FACTUAL` (proceed to retrieval) or `REFUSE` with a reason and a matching educational link (SEBI riskometer page for advice refusals, the relevant scheme's official factsheet link for performance refusals, a generic "we don't handle personal information" message for PII with the input not logged verbatim).
- Unit-testable: a small standalone test list of ~15 questions covering all four buckets (factual, PII, advice, performance) with expected outcomes.

**Files:** `src/app/guardrails.py`, `tests/test_guardrails.py` (or an inline test block if no separate test setup exists).

**Done when:** all sample questions in the guardrail test list route to the correct outcome without needing the LLM or ChromaDB.

## Phase 4 — Retrieval
**Build:**
- `src/app/retriever.py`: embeds a factual (already-guardrail-cleared) question using the Phase 2 embedder, queries ChromaDB for top-k chunks (default k=4), and returns them with similarity scores.
- Low-confidence handling: if the best score is below a set threshold, return a `NO_MATCH` result instead of weak chunks, so the caller can short-circuit to an "I don't have that in my sources" response.

**Files:** `src/app/retriever.py`.

**Done when:** manually testing each of the 6 example factual questions from the PRD returns the correct source's chunk in the top-2 results.

## Phase 5 — Generation (LLM)
**Build:**
- `src/app/generate.py`: builds the system prompt (answer only from provided chunks; ≤3 sentences; cite exactly one source URL from the top chunk; append "Last updated from sources: <date>"; say so plainly if the chunks don't answer the question), calls Groq (`openai/gpt-oss-120b`) with the question + retrieved chunks + last-10-turn memory, and returns the formatted answer.
- Wires guardrails (Phase 3) → retriever (Phase 4) → generation into one function, `answer_question()`, used by the UI.
- Conversation memory: a simple rolling list of the last 10 (question, answer) pairs, passed as context but never bypassing the guardrail check on each new message.

**Files:** `src/app/generate.py`, `src/app/pipeline.py` (the `answer_question()` orchestrator).

**Done when:** all 10 PRD example questions (6 factual + 4 refuse) produce correct, correctly-formatted answers end to end via `answer_question()`.

## Phase 6 — UI
**Build:**
- `src/app.py`: Streamlit app — welcome line, 3 clickable example questions, fixed disclaimer text, chat input/output using `answer_question()`, citation rendered as a clickable link, no PII-inviting form fields anywhere.

**Files:** `src/app.py`.

**Done when:** `streamlit run src/app.py` runs locally, and manually asking all 10 PRD example questions through the UI gives correct, correctly-formatted, correctly-cited (or correctly-refused) answers.

## Phase 7 — Submission packaging
**Build:**
- `README.md`: setup steps, scope (Groww / HDFC MF / 4 schemes), how to get a Groq key, how to run ingestion then the app, known limits (static corpus, English-only, no real-time NAV). Done.
- `sample_qna.md`: the 10 PRD example questions with the assistant's actual answers and citation links (or refusal message), generated by actually running the app. Done — generated 2026-09-28 against the running app.
- Disclaimer snippet documented in the README, matching what's shown in the UI. Done.
- Push to the public GitHub repo, deploy to a free host, set env vars, and confirm the public URL loads and answers correctly.

**Files:** `README.md`, `sample_qna.md`, `render.yaml`, `src/app.py` (self-build-on-empty logic), final commit + push, deployment.

**Status (2026-09-28):** pushed to GitHub. Tried Render first: `render.yaml` (a Blueprint with the build/start commands below and `GROQ_MODEL` pre-set) deployed, build succeeded, health check passed ("Live"), but real requests 502'd - most likely Render's free-tier 512MB RAM ceiling, since torch/sentence-transformers/chromadb together are memory-heavy. Pinned `requirements.txt` to the CPU-only torch wheel (much smaller than the default CUDA-bundled Linux build) to reduce the footprint; the 502s persisted, so pivoting to **Streamlit Community Cloud** (1GB RAM on its free tier, and purpose-built for Streamlit apps) as the primary deploy target, keeping `render.yaml`/Render as a documented alternative for a paid tier.
- Render build command: `pip install -r requirements.txt && python -m src.ingest.run`; start command: `python -m streamlit run src/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`.
- Streamlit Community Cloud has no equivalent build-command hook (only `pip install -r requirements.txt`, then it runs the app directly) - so `src/app.py` now checks the vector store on load and self-builds it (chunk + embed from the committed `data/raw/`) if empty, via a `@st.cache_resource`-wrapped function that runs at most once per process. Verified locally: deleted the ChromaDB collection to simulate a fresh deploy, started the app, watched it show a one-time "Setting up..." spinner (~25s) then serve a correct, cited answer on the very next question.
- Not yet confirmed live on a public URL - awaiting the account holder's Streamlit Community Cloud deploy.

**Done when:** the public Render URL is reachable with no login, answers the sample questions correctly, and the GitHub repo has everything the brief's deliverables list requires (working prototype link, 10-source list, README, sample Q&A file, disclaimer snippet).

## Summary table
| Phase | Deliverable | Depends on |
|---|---|---|
| 0 | Repo scaffold | — |
| 1 | Load & Chunk | 0 |
| 2 | Embed & Store | 1 |
| 3 | Guardrails | 0 |
| 4 | Retrieval | 2 |
| 5 | Generation | 3, 4 |
| 6 | UI | 5 |
| 7 | Submission packaging | 6 |
