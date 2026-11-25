# Follow order NQ-103

[Back to README](../README.md) · [Architecture](ARCHITECTURE.md)

| Event | Date |
| --- | --- |
| Purchased | January 1, 2025 |
| Delivered | January 10, 2025 |
| Return requested | January 31, 2025 |
| Refund posted | February 7, 2025 |

1. **Select the population.** `audit("2025-02")` includes the order because its refund belongs to February. The request date does not decide which report contains the row.
2. **Choose the edition.** January 1 is the inclusive start of the 2025 edition. The purchase date must match exactly one edition interval.
3. **Find the required rules.** `data/2025-A.md` specifies a 21-day standard window and no holiday extension. The audit retrieves the named clauses, independently of the assistant's search ranking.
4. **Calculate in SQLite.** The standard deadline is January 31. The request delta is zero; the refund delta is seven days. The row becomes `on_time`, with `days_late=0` and `false_alarm=true`.
5. **Inspect the evidence.** Select the row in the browser or open [the saved JSON report](../examples/february-audit.json). The sources map resolves each policy citation to the corresponding file and clause text.
6. **Ask the model.** The browser posts a question to `/api/ask`. The server builds the selected-month audit and the assistant validates the input. For a normal question, the model can request `read_audit()`, `search_policy(query, edition)` or `read_policy(edition)`. Python executes the read-only functions and sends the evidence back to the model. The answer and tool trace return to the browser after reference checks. Those checks do not establish that every claim is correct.

## Try the other paths

- Ask why NQ-106 was on time. Its standard February 19 deadline is later than the qualifying holiday floor of January 31. This question can combine audit facts and retrieved policy clauses.
- Compare both policy editions across their four sections. The new `read_policy` tool can provide the complete clauses for each edition in two calls.
- Ask why NQ-999 was late. A single unavailable ID is handled by Python before calling the model; the answer should explain that its status cannot be determined in the selected audit.
- Inspect NQ-108. A missing request date prevents a defensible lateness finding.

## Code map

| File | Responsibility |
| --- | --- |
| `data/ledger.csv`, `data/editions.json`, `data/*.md` | Ledger, edition intervals and source policies |
| `returnledger/policy.py` | Section parsing, lexical ranking and supported rule grammar |
| `returnledger/audit.py` | Validation, monthly selection, SQL arithmetic and evidence |
| `returnledger/assistant.py` | Input pre-check, model requests, three tools, logging and reference checks |
| `returnledger/web.py`, `returnledger/static/` | Local HTTP server and browser UI |
| `returnledger/evaluate.py` | Compare outputs with audit and retrieval fixtures |

## Experiments

Work in a temporary copy. Replace the 2025 standard window of 21 calendar days with 24 calendar days, preserving the rest of the supported sentence. Re-run February: NQ-104 should move to on time. The frozen evaluation should report a mismatch because it describes the original rule. Restore the policy, then try unsupported wording such as “three working weeks”. The parser should send affected stock orders to manual review. Restore the original file again.

For retrieval, search with a policy term such as `holiday`, then try a synonym-only query. Lexical retrieval may miss it. Compare this with `read_policy`, which exposes all sections of one edition and does not depend on keyword ranking.

The distinction matters: missing a relevant clause is undesirable for a conversational answer, but silently missing a mandatory rule would invalidate a calculated audit decision. The audit therefore uses exact section lookup, not RAG ranking.
