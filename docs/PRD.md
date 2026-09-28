# PRD: Facts-Only Mutual Fund FAQ Assistant

**Product context:** Groww | **AMC scoped:** HDFC Mutual Fund | **Milestone:** NextLeap Milestone 4 (due Oct 2, 2026, 11:59 PM IST)

## Goal
Build a RAG chatbot that answers factual questions about a small set of HDFC mutual fund schemes (expense ratio, exit load, minimum SIP, ELSS lock-in, riskometer, benchmark, and how to download statements) using only 10 official AMC/SEBI pages as its knowledge base. Every factual answer must carry exactly one citation link. The assistant must refuse opinion, advice, or performance-comparison questions rather than answer them.

## Target users
- **Retail investors** on Groww comparing HDFC schemes, who want a quick factual answer with a source they can verify, not a recommendation.
- **Support/content teams** who currently answer the same repetitive scheme questions by hand and want a first-line, citation-backed assistant.

## In scope
- Answering factual questions about the 4 scoped HDFC schemes (Large Cap, Flexi Cap, ELSS Tax Saver, Mid Cap): expense ratio, exit load, minimum SIP, ELSS lock-in period, riskometer level, benchmark index.
- Explaining how to download a consolidated account statement or a capital-gains statement (process only, no personal data handled).
- One citation link per answer, drawn only from the 10-source corpus.
- Politely refusing: investment advice ("should I buy/sell"), performance claims or return comparisons, and any question needing personal data (PAN, Aadhaar, phone, email, OTP, account number).
- A small chat UI: welcome line, 3 example questions, and a fixed "Facts-only. No investment advice." disclaimer.
- Answers capped at 3 sentences, ending with "Last updated from sources: <date>".

## Out of scope
- Any scheme outside the 4 chosen HDFC funds, or any AMC other than HDFC.
- Investment advice, portfolio suggestions, or "which fund is better" comparisons.
- Computing, estimating or comparing returns/performance.
- Accepting, storing or echoing back PII (PAN, Aadhaar, phone, email, OTP, folio/account numbers).
- Real-time or transactional actions (placing SIPs, redemptions, actual statement generation) — the assistant only explains the public process and links to it.
- Multi-turn portfolio tracking or account login.

## Example user questions
**Should answer (factual, in scope):**
1. "What is the expense ratio of HDFC ELSS Tax Saver?"
2. "What is the minimum SIP amount for HDFC Large Cap Fund?"
3. "What is the lock-in period for HDFC ELSS Tax Saver?"
4. "What is the exit load on HDFC Flexi Cap Fund?"
5. "What is the riskometer level and benchmark for HDFC Mid Cap Fund?"
6. "How do I download my capital gains statement?"

**Should refuse (out of scope, with an educational link instead):**
7. "Should I invest in HDFC ELSS or HDFC Flexi Cap?"
8. "Which HDFC fund gave the best returns last year?"
9. "Is now a good time to buy HDFC Mid Cap Fund?"
10. "My PAN is ABCDE1234F, can you check my portfolio?"

## Success criteria
- **Citation accuracy:** every factual answer's link resolves to a source in the 10-source corpus that actually supports the stated fact (target: 100% on the sample Q&A set).
- **Answer vs. refuse judgement:** correctly answers all in-scope factual questions and correctly refuses all advice/performance/PII questions in the sample Q&A set (target: 100% on the 10 example questions above, used as the grading set).
- **Format compliance:** answers stay at 3 sentences or fewer and include the "Last updated from sources" line.
- **No hallucinated facts:** no numeric value (ratio, amount, lock-in period) appears in an answer unless it is present in the retrieved chunk.
- **Working, hosted prototype:** reachable at a public Render URL with no login required, responding within a few seconds per query.
- **Grader can reproduce it:** README lets someone clone the repo, add their own Groq key, and run it locally in under 10 minutes.

## Constraints
- **Sources:** exactly the 10-URL corpus already verified (4 HDFC scheme pages, 2 SID PDFs, HDFC statement page, HDFC capital-gains guide, SEBI riskometer page, SEBI TER circular). No blogs, no third-party sites.
- **No PII:** never accept, store, or log PAN, Aadhaar, account numbers, OTPs, emails, or phone numbers; detect and refuse before the query reaches the LLM.
- **No performance claims:** never compute or compare returns; redirect to the official factsheet.
- **Stack is fixed:** Python, sentence-transformers/all-MiniLM-L6-v2 embeddings, ChromaDB (persisted to disk), Groq LLM (`openai/gpt-oss-120b`), Streamlit UI, hosted on Render. Secrets in `.env`, never committed.
- **Deliverables:** working prototype link, 10-source list (CSV/MD), README (setup, scope, known limits), sample Q&A file (5–10 queries with answers and links), disclaimer snippet — all in a public GitHub repo.
- **Timeline:** submit by Oct 2, 2026, 11:59 PM IST.
