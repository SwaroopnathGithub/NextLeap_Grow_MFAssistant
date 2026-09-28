# Architecture: Facts-Only Mutual Fund FAQ Assistant

Derived from PRD.md. Two independent pipelines, as required: **Ingestion** (run once, offline) and **Query** (run per user question, online).

## 1. System overview

```
                         INGESTION (run once / on data change)
 ┌──────────┐   ┌───────────┐   ┌────────────────────┐   ┌──────────────────┐
 │ 10 source │──▶│  Loader   │──▶│  Chunker            │──▶│  Embedder          │
 │ URLs/PDFs │   │ (fetch +  │   │ (splits + attaches  │   │ (MiniLM-L6-v2,     │
 │ (sources. │   │  extract  │   │  metadata: source   │   │  384-dim vectors)  │
 │  csv)     │   │  text)    │   │  url, scheme, field)│   │                    │
 └──────────┘   └───────────┘   └────────────────────┘   └────────┬──────────┘
                                                                    ▼
                                                          ┌───────────────────┐
                                                          │  ChromaDB (disk-   │
                                                          │  persisted vector  │
                                                          │  store)            │
                                                          └───────────────────┘

                         QUERY (run per request)
 ┌──────────┐   ┌───────────────┐   ┌─────────────┐   ┌────────────┐   ┌────────────────┐   ┌──────────┐
 │  User     │──▶│  Guardrail    │──▶│  Embed      │──▶│  Retrieve  │──▶│  LLM (Groq      │──▶│  Answer +│
 │  question │   │  classifier   │   │  question   │   │  top-k     │   │  llama-3.3-70b) │   │  citation│
 │  (Stream- │   │  (PII / advice│   │  (same      │   │  chunks    │   │  + system       │   │  + "Last │
 │  lit UI)  │   │  / factual /  │   │  MiniLM     │   │  from      │   │  prompt +       │   │  updated"│
 │           │   │  out-of-scope)│   │  model)     │   │  ChromaDB  │   │  retrieved      │   │  line    │
 └──────────┘   └───────┬───────┘   └─────────────┘   └────────────┘   │  chunks         │   └──────────┘
                         │ refuse path                                  └─────────────────┘
                         ▼
                 Polite refusal +
                 educational link
                 (no LLM/DB call)
```

## 2. Components

### 2.1 Loader (`src/ingest/loader.py`)
- Reads `sources.csv` (10 rows: url, source_type, scheme, covers).
- For HTML pages: fetch and strip to clean text (main content only — nav/footer/scripts removed).
- For the 2 SID PDFs: extract text per page.
- Output: one raw text file per source under `data/raw/`, named by source id, plus a `data/raw/manifest.json` recording {id, url, scheme, source_type, fetched_at}.
- Failure handling: if a fetch fails, log it and skip that source rather than halting ingestion; the manifest marks it `status: failed`.

### 2.2 Chunker (`src/ingest/chunker.py`)
- **Decided after inspecting the actual sources** (per the session's instruction), not fixed blindly. Rationale given at build time in `data/chunks/chunking_notes.md`.
- Expected approach given the data shape (short fact-dense scheme pages + longer structured PDFs): a **semantic/structural** split first (by heading or fact block, e.g. "Expense Ratio", "Exit Load", "Riskometer") falling back to a **fixed-size split with overlap** (target: ~200–400 tokens per chunk, ~15–20% overlap) for pages/PDFs with no clean structure.
- Each chunk carries metadata: `source_id`, `source_url`, `scheme_name`, `field_hint` (e.g. "expense_ratio", "lock_in", "statement_howto" where identifiable), `fetched_at`.
- All chunks written to `data/chunks/chunks.txt` (human-readable, one chunk per block with its metadata header) for inspection before embedding.

### 2.3 Embedder (`src/ingest/embedder.py`)
- Model: `sentence-transformers/all-MiniLM-L6-v2`, loaded once, run locally (no API key, no network call at embed time).
- Embeds every chunk in `data/chunks/chunks.txt` into a 384-dim vector.
- The exact same model instance/config is reused at query time to embed the user's question, so both live in the same vector space.

### 2.4 Vector store (`src/ingest/store.py`)
- ChromaDB, persisted to a local folder (`data/chroma/`) so ingestion is a one-time step (`python -m src.ingest.run`), not something that reruns on every app boot.
- One collection: `mf_faq_chunks`. Each entry: `{id, embedding, document (chunk text), metadata}`.
- Re-running ingestion clears and rebuilds the collection deterministically (idempotent), so refreshing sources is one command.

### 2.5 Guardrail classifier (`src/app/guardrails.py`)
Runs **before** any retrieval or LLM call, on every incoming question:
1. **PII check** (regex-based): PAN pattern, Aadhaar pattern, email, phone number, OTP-like 4–6 digit codes paired with words like "OTP"/"verify". Any match → immediate refusal, question is not logged verbatim, no LLM/DB call made.
2. **Advice/opinion check**: keyword + pattern match for "should I", "buy or sell", "which is better", "recommend", "worth investing" → immediate polite refusal with an educational link (SEBI riskometer page), no LLM/DB call made.
3. **Performance/comparison check**: "returns", "performance", "compare", "which fund gave more" → refusal, points to the official factsheet, no computation attempted.
4. Anything not caught by 1–3 is treated as **factual** and proceeds to retrieval.
This keeps refusals deterministic and cheap (no LLM cost on out-of-scope questions), matching the PRD's "answer vs. refuse" success criterion.

### 2.6 Retriever (`src/app/retriever.py`)
- Embeds the (already-cleared) factual question with the same MiniLM model.
- Queries ChromaDB for top-k chunks (k starts at 4, tunable) by cosine similarity.
- If the best match's similarity is below a set threshold, treat as **low-confidence**: skip the LLM and return an "I don't have that in my sources" message with a link to the relevant scheme page, rather than let the LLM guess.

### 2.7 LLM answer generation (`src/app/generate.py`)
- Provider: Groq API, model `openai/gpt-oss-120b` (key from `.env` → `GROQ_API_KEY`, model id from `.env` → `GROQ_MODEL`, never hardcoded, never committed).
- System prompt encodes: answer only from provided chunks; ≤3 sentences; cite exactly one source URL (the top retrieved chunk's `source_url`); end with "Last updated from sources: <fetched_at of that chunk>"; if the chunks don't contain the answer, say so instead of guessing.
- Conversation memory: last 10 turns kept and passed as context (per the session's instruction), so follow-up questions ("what about its exit load?") resolve correctly, but memory never overrides the guardrail check, which runs fresh on every new message.

### 2.8 UI (`src/app.py`, Streamlit)
- Welcome line + 3 clickable example questions + fixed disclaimer text ("Facts-only. No investment advice.").
- Chat input → guardrail → (retrieve → generate) or (refusal) → rendered answer with the citation as a clickable link.
- No fields for PAN/email/phone are ever rendered — nothing in the UI invites PII entry.

## 3. Data flow summary
```
sources.csv → loader → data/raw/*.txt → chunker → data/chunks/chunks.txt
   → embedder → ChromaDB (data/chroma/)                         [INGESTION, once]

user question → guardrail → [refuse] OR [embed → retrieve top-k from ChromaDB
   → Groq LLM + system prompt + chunks → answer + citation]     [QUERY, per request]
```

## 4. Repo layout
```
groww-mf-faq-assistant/
├── src/
│   ├── ingest/
│   │   ├── loader.py
│   │   ├── chunker.py
│   │   ├── embedder.py
│   │   ├── store.py
│   │   └── run.py            # orchestrates the full ingestion pipeline
│   └── app/
│       ├── guardrails.py
│       ├── retriever.py
│       ├── generate.py
│       └── app.py            # Streamlit entrypoint (referenced as src/app.py by Render)
├── data/
│   ├── raw/                  # fetched source text + manifest.json
│   ├── chunks/               # chunks.txt + chunking_notes.md
│   └── chroma/               # persisted vector DB (gitignored — rebuilt by ingestion)
├── sources.csv                # the 10-source list
├── sample_qna.md               # 5-10 sample Q&A with answers + links (deliverable)
├── requirements.txt
├── .env.example                # GROQ_API_KEY=, GROQ_MODEL=openai/gpt-oss-120b
├── .gitignore                  # .env, data/chroma/
└── README.md
```

## 5. Deployment
Two hosting paths, both documented in the README:
- **Streamlit Community Cloud (recommended):** no custom build-command hook available
  (only `pip install -r requirements.txt`, then the app starts directly), so
  `src/app.py` checks the vector store on load and self-builds it (chunk + embed) if
  empty, cached with `@st.cache_resource` so it only runs once per process. 1 GB RAM
  on its free tier, vs. 512 MB on Render's - meaningfully more headroom for
  torch/sentence-transformers/chromadb.
- **Render (alternative):** `render.yaml` Blueprint with build command
  `pip install -r requirements.txt && python -m src.ingest.run` and start command
  `python -m streamlit run src/app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true`.
  In testing, Render's free tier (512 MB RAM) reached "Live" but then 502'd on real
  requests even after pinning the CPU-only torch build - most likely a RAM ceiling once
  the embedding model and vector store actually load. Works fine on a paid Render tier
  with more memory.
- Env vars (either host, not in the repo): `GROQ_API_KEY`, `GROQ_MODEL`.
- `data/chroma/` is gitignored and rebuilt from the committed `data/raw/` + `sources.csv`
  on first run/build, keeping the corpus in sync with `sources.csv` without needing
  network access at deploy time.

## 6. How this maps to the PRD's success criteria
| PRD success criterion | Architecture mechanism |
|---|---|
| Citation accuracy | Each chunk keeps its exact `source_url`; the answer cites the retrieved chunk's own URL, never a guessed one. |
| Answer vs. refuse judgement | Deterministic guardrail classifier runs before retrieval/LLM, independent of model behavior. |
| Format compliance (≤3 sentences, "Last updated" line) | Enforced in the system prompt given to the LLM at generation time. |
| No hallucinated facts | Low-confidence retrieval short-circuits to an "I don't know" response instead of reaching the LLM with weak context. |
| Working hosted prototype | Streamlit Community Cloud (or Render) deployment; the app self-builds its index on first run if needed, so it works without a host-specific build hook. |
| Reproducible by a grader | `.env.example`, `requirements.txt`, and README setup steps are all committed. |
