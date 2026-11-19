# Follow order NQ-103

| Event | Date |
| --- | --- |
| Purchased | January 1, 2025 |
| Delivered | January 10 |
| Return requested | January 31 |
| Refund posted | February 7 |

1. **Select the population.** The refund posted in February, so `audit("2025-02")` includes this order. SQL filters the refunded column in the in-memory ledger. March 1 belongs to the next report.
2. **Choose the edition.** The purchase occurred on January 1, exactly when the 2025 edition began. The edition map uses an inclusive start and an exclusive end. Zero or multiple matches send the order to review.
3. **Retrieve the required clauses.** Open data/2025-A.md. The standard section gives 21 calendar days from delivery. The holiday section says no extension applies. The edition and section form a stable citation such as `2025-A#standard`.
4. **Calculate.** In returnledger/audit.py the CALCULATE query adds 21 days to January 10. The request is on January 31, so its delay is zero. Repeating the same subtraction with the refund date gives seven days. That disagreement sets the false_alarm flag.
5. **Inspect the evidence.** Open the row in the browser or look it up in examples/february-audit.json. Each citation leads to the exact text evaluated. The JSON records the evidence as it was at run time.
6. **Ask the model.** The browser sends a question and month to /api/ask. Python offers two read-only functions, validates the requested arguments, executes them, and sends tool results back to the model. The final response is checked for unexposed order IDs and bracketed policy references. This check cannot certify reasoning or detect every unsupported statement.

## Code map

| File | Responsibility |
| --- | --- |
| data/ledger.csv, data/editions.json, data/*.md | Raw records, edition intervals and policy passages |
| returnledger/policy.py | Parse section headers, rank passages, interpret supported deadline wording |
| returnledger/audit.py | Load SQLite, scope the month, compute deadlines and attach evidence |
| returnledger/assistant.py | Provider request, bounded tool loop, argument and reference checks |
| returnledger/web.py, returnledger/static/ | Local HTTP API and browser interface |
| returnledger/evaluate.py | Compare independent expected rows and ranked passages with actual results |

## Two design choices worth testing

Make a temporary copy and replace “21 calendar days” with “24 calendar days” in the 2025 edition. Rerun February. NQ-104 changes to on time. The frozen evaluation should now report a mismatch. Restore the source and try “three working weeks.” The parser cannot give that wording a dependable deadline and routes stock orders in that edition to review.

Policy search is lexical: it counts shared terms and gives rarer terms more weight within the edition. This tiny corpus makes it possible to inspect every result. A synonym-only query can miss the relevant section. Deterministic auditing uses exact required section IDs because skipping the holiday clause would silently change deadlines.
