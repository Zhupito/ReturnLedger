# ReturnLedger

A refund posted on February 7. The customer asked to return the item on January 31, the last day they were eligible. Should that refund show up in a late-return report?

ReturnLedger answers that question for a fictional shop, North Quay Supply. It joins an order timeline to the policy edition in force at purchase, calculates a deadline in SQLite, and shows the clauses behind the finding. The optional RAG assistant can search the policy and call a read-only audit tool to explain a result.

![NQ-103 timeline: purchased January 1, delivered January 10, requested on the January 31 deadline, refunded February 7.](docs/assets/timeline.png)

## Run locally

From the folder containing this README, run the following with Python 3.11 or 3.12.

```shell
python -m returnledger serve
```

Open **http://127.0.0.1:8080**. On Windows, use `py -3.12` in place of `python` if needed. The ledger, policy search, JSON download, tests, and evaluation use the Python standard library and run offline. See [Start here](START_HERE.md) for Windows setup and live model configuration.

## Try the February 2025 audit

| Finding | Orders | Why it matters |
| --- | ---: | --- |
| Late request | 3 | Each was requested one day after the effective deadline. |
| On time | 4 | All four would be wrongly flagged if the refund date were used. |
| Manual review | 4 | One custom item, two incomplete timelines, one uncovered purchase date. |

Select **NQ-103** to inspect the January 31 deadline. Then open **NQ-106**. Its holiday rule extends the deadline only *if later*. February 19, the ordinary deadline, already gives the customer more time than the January 31 holiday cutoff.

[Browse the February audit snapshot](examples/february.md) · [Inspect its machine-readable evidence](examples/february-audit.json)

## Where the LLM fits

The assistant receives a question and two tool definitions. It can request `search_policy(query, edition)` to retrieve ranked passages or `read_audit()` to inspect the selected month's decisions and quoted evidence. The next model call receives those tool results. The interface displays the answer and tool names. Try “Why was NQ-106 on time even though the holiday cutoff was January 31?”

The monthly audit has a separate deterministic path. It looks up mandatory clauses by edition and section, parses a small supported grammar, and passes dates and values into parameterized SQL. This makes calculations reproducible with or without the LLM.

## Reproduce the checks

```shell
python -m unittest discover -v
python -m returnledger evaluate
python -m returnledger audit --month 2025-02
```

The included fixtures check 11 February orders and 8 edition-scoped search queries. They use synthetic examples written for this project. The search benchmark measures first-result accuracy on those queries. It doesn't estimate performance on customer data.

| Read next | Contents |
| --- | --- |
| [Walkthrough](docs/WALKTHROUGH.md) | Follow one order from CSV to SQL to evidence. |
| [Evaluation](docs/EVALUATION.md) | Expected values, measured results, gaps and failure examples. |
| [Interview guide](docs/INTERVIEW_GUIDE.md) | A short demo, design questions, and suggested CV wording. |
| [Related work](docs/RELATED_WORK.md) | Similar public projects and the scope of this implementation. |
| [Publish on GitHub](docs/GITHUB_UPLOAD.md) | Commands for the extracted project. |

Implementation and documentation were prepared with AI assistance. All orders, policy text and expected outcomes are fictional. The demo assumes one item, one request and at most one posted refund per order; it doesn't determine real customer eligibility.
