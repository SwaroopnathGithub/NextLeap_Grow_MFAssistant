# Groww MF Facts-Only Assistant (NextLeap Milestone 4)

A RAG chatbot that answers **factual** questions about 4 HDFC Mutual Fund schemes
(expense ratio, exit load, minimum SIP, ELSS lock-in, riskometer, benchmark, and how
to download statements), citing exactly one official source per answer. It refuses
investment advice, performance comparisons, and any request involving personal
information (PAN, Aadhaar, phone, email, OTP).

Framed for **Groww** as the reference product; scope is **HDFC Mutual Fund**,
schemes: Large Cap, Flexi Cap, ELSS Tax Saver, Mid Cap.

Full docs: [`docs/PRD.md`](docs/PRD.md) · [`docs/architecture.md`](docs/architecture.md) · [`docs/implementation.md`](docs/implementation.md)

## Status
Phases 0-6 built and tested locally (ingestion, guardrails, retrieval, generation, UI),
pushed to GitHub. `render.yaml` is committed and ready; the actual Render deploy (an
account-holder action) is the one remaining step. See `docs/implementation.md` for the
phased build plan and `sample_qna.md` for real answers from the running app.

## Setup
1. `pip install -r requirements.txt` (a virtualenv is recommended: `python -m venv .venv`)
2. Copy `.env.example` to `.env` and add your own `GROQ_API_KEY` (get one free at https://console.groq.com/keys)
3. `python -m src.ingest.run` — builds the chunk file and vector index (`data/chroma/`).
   The 10 source pages/PDFs are already fetched and committed under `data/raw/` (see
   "Known limits" below for why), so this step only re-chunks and re-embeds; it doesn't
   need network access.
4. `streamlit run src/app.py` — starts the chatbot locally at http://localhost:8501

### Running the tests
`python -m pytest tests/ -q` — chunker and guardrail unit tests (11 cases total), no
API key or network required.

## Deploying to Render
`render.yaml` in the repo root is a Render Blueprint with the build/start commands and
`GROQ_MODEL` pre-filled:
1. On [render.com](https://render.com), New > Blueprint, connect this GitHub repo.
2. Render reads `render.yaml` and proposes the `groww-mf-facts-only-assistant` web
   service. Confirm.
3. It will prompt for the one `sync: false` env var: `GROQ_API_KEY`. Paste your key.
4. Deploy. Build runs `pip install -r requirements.txt && python -m src.ingest.run`
   (re-chunks and re-embeds from the committed `data/raw/`, no network fetch needed -
   see "Known limits" below); start runs the Streamlit app bound to Render's `$PORT`.

## Known limits
- **Static corpus.** The knowledge base is exactly the 10 sources in `sources.csv`,
  fetched once. It does not reflect live NAVs, returns, or scheme changes after the
  fetch date recorded in `data/raw/manifest.json`. Re-run ingestion (after refreshing
  `data/raw/`) to pick up changes.
- **hdfcfund.com and investor.sebi.gov.in block plain HTTP fetches.** Both sit behind
  Akamai bot protection that returns `403` to `requests`/`curl` from any machine, not
  just a sandboxed one — only a real browser engine gets through. `src/ingest/loader.py`
  still implements the plain-HTTP fetch path per the architecture doc, but
  `src/ingest/run.py` skips it and re-chunks/re-embeds from the already-committed
  `data/raw/*.txt` files instead, so ingestion (including Render's build-time run) stays
  reliable. If you need to refresh the source pages, re-fetch the 6 affected HTML pages
  with a real browser and the 2 SID PDFs / 1 SEBI circular PDF via direct download (see
  `data/raw/manifest.json` for the exact URLs and method used per source), then delete
  `data/raw/manifest.json` (or edit a record's `status` away from `"ok"`) so
  `src/ingest/run.py` re-fetches instead of skipping.
- **English-only.**
- **No real-time NAV or transaction actions.** The assistant explains the public
  process for downloading statements; it never files a request or handles real PAN/
  folio/OTP data.
- **PDF text extraction is imperfect.** The 2 SID PDFs are 74 pages of dense
  regulatory text; `pypdf`'s extraction occasionally merges unrelated lines. The scheme
  facts most likely to be asked about (expense ratio, exit load, min SIP, lock-in,
  riskometer, benchmark) are additionally chunked as compact per-fact statements
  straight from the scheme pages (see `data/chunks/chunking_notes.md`), so this mainly
  affects the SIDs' role as secondary/regulatory context, not the primary facts.

## Disclaimer
This assistant is facts-only and does not provide investment advice.
