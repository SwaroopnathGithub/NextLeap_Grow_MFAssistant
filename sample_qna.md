# Sample Q&A

The 10 example questions from `docs/PRD.md`, run through the real app
(`src/app/pipeline.py`'s `answer_question()`) on 2026-09-28, using the
`openai/gpt-oss-120b` model on Groq. Exact output, unedited.

## Factual (should answer)

**Q1. What is the expense ratio of HDFC ELSS Tax Saver?**
> The expense ratio (TER) for HDFC ELSS Tax Saver is 1.21.
>
> Last updated from sources: 2026-09-28

Source: https://www.hdfcfund.com/explore/mutual-funds/hdfc-elss-tax-saver/direct

**Q2. What is the minimum SIP amount for HDFC Large Cap Fund?**
> The minimum SIP amount for HDFC Large Cap Fund is ₹ 100.
>
> Last updated from sources: 2026-09-28

Source: https://www.hdfcfund.com/explore/mutual-funds/hdfc-large-cap-fund/direct

**Q3. What is the lock-in period for HDFC ELSS Tax Saver?**
> The lock-in period for HDFC ELSS Tax Saver is three years.
>
> Last updated from sources: 2026-09-28

Source: https://www.hdfcfund.com/explore/mutual-funds/hdfc-elss-tax-saver/direct

**Q4. What is the exit load on HDFC Flexi Cap Fund?**
> The exit load for HDFC Flexi Cap Fund is 1.00% when units are redeemed or switched out within one year of allotment.
>
> Last updated from sources: 2026-09-28

Source: https://www.hdfcfund.com/explore/mutual-funds/hdfc-flexi-cap-fund/direct

**Q5. What is the riskometer level and benchmark for HDFC Mid Cap Fund?**
> The HDFC Mid Cap Fund has a "Very High" riskometer level and its benchmark is the NIFTY Midcap 150 Index.
>
> Last updated from sources: 2026-09-28

Source: https://www.hdfcfund.com/explore/mutual-funds/hdfc-mid-cap-fund/direct

**Q6. How do I download my capital gains statement?**
> You can download your capital-gain statement by logging into the mutual-fund distributor platform you use, going to its tax or reports section, and selecting the required financial year. Alternatively, you can visit each fund house's website, log in with your PAN or email, and generate the statement there; many AMCs also let you download a consolidated statement for all your schemes. A third option is to request the statement through the Consolidated Account Statement (CAS) service via CAMS or NSDL, choosing the "capital gains" format.
>
> Last updated from sources: 2026-09-28

Source: https://www.hdfcfund.com/learn/blog/how-get-capital-gain-statement-mutual-fund-schemes-india

## Out of scope (should refuse)

**Q7. Should I invest in HDFC ELSS or HDFC Flexi Cap?**
> I can't give investment advice or recommendations. For help matching a scheme's risk level to your own risk appetite, see SEBI's riskometer guide: https://investor.sebi.gov.in/riskometer.html

Refusal reason: advice

**Q8. Which HDFC fund gave the best returns last year?**
> I don't compute or compare fund returns or performance. For official performance figures, check the relevant scheme's official page on hdfcfund.com (Downloads > SID / Fund Facts).

Refusal reason: performance

**Q9. Is now a good time to buy HDFC Mid Cap Fund?**
> I can't give investment advice or recommendations. For help matching a scheme's risk level to your own risk appetite, see SEBI's riskometer guide: https://investor.sebi.gov.in/riskometer.html

Refusal reason: advice

**Q10. My PAN is ABCDE1234F, can you check my portfolio?**
> I can't accept or process personal information (PAN, Aadhaar, phone, email, or similar identifiers) - please don't share that here.

Refusal reason: PII (the guardrail catches this before any LLM/DB call, and the raw question is not logged verbatim)
