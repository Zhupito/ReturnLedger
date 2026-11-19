# What the checks measure

Run `python -m returnledger evaluate` to compare the application with two static answer keys. The command exits nonzero on mismatch. The recorded output is in [evaluation.json](../examples/evaluation.json).

| Check | Result on the bundled fixtures | Scoring rule |
| --- | --- | --- |
| February ledger | 11 of 11 | Order set, status, deadline, days late and false-alarm flag agree with the key. |
| Policy retrieval | 8 of 8 | Expected section is the top hit in the specified edition. |
| Refund-date comparison | 4 false alarms among 7 decidable cases | Swap the request date for the payment date while keeping the deadline fixed. Four additional orders become late. |

### Inspect the answer key

NQ-102 qualified for the 2024 holiday window through January 31. Its February 1 request was one day late. NQ-105 was purchased December 25, just outside the holiday purchase interval. It has a February 9 standard deadline under the 2024 edition. NQ-106 has both a holiday floor and a later ordinary deadline. NQ-110 has a purchase before the first edition; the expected deadline and lateness are blank.

The 11 cases and eight search queries are development fixtures. They use the same vocabulary as the policies. The 8/8 result says little about paraphrases. For example, searching for “festive grace period” returns no passage with the current tokenizer. No general answer-faithfulness score has been measured.

### Test boundaries

The unit suite covers changed prose, incomplete records, missing and overlapping editions, duplicate mandatory sections, date order, month boundaries, tool argument validation, bounded rounds, unknown references and the HTTP adapter with simulated model replies. The live provider, Docker build, Windows execution and hosted GitHub Actions require separate verification. The in-memory database rebuild is intended for a small local ledger.

An LLM can cite the right order and still state the wrong number of days. For a live check, ask for all three February late orders, verify their IDs and delays against the exported JSON, then ask about NQ-108 and verify the model explains the missing request date. Record the model name, date and any discrepancies before quoting an answer-quality metric.
