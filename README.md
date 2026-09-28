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
🚧 Under active development. See `docs/implementation.md` for the phased build plan.

## Setup (once the app is built)
1. `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and add your own `GROQ_API_KEY` (get one free at https://console.groq.com/keys)
3. `python -m src.ingest.run` — builds the vector index from `sources.csv` (run once)
4. `streamlit run src/app.py` — starts the chatbot locally

## Disclaimer
This assistant is facts-only and does not provide investment advice.
