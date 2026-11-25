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

### Automated test coverage

The application includes 38 automated tests implemented using Python's
standard-library unittest framework.

| Test module | Tests | Main responsibility |
|---|---:|---|
| test_audit.py | 14 | Business rules, SQL calculations and data validation |
| test_assistant.py | 8 | Tool execution, response validation and error handling |
| test_assistant_extended.py | 12 | Full-policy retrieval and missing-order handling |
| test_web.py | 4 | HTTP endpoints and API request structure |
| Total | 38 | |

Assistant tests use simulated model responses to ensure reproducible,
offline testing without API charges.

### Live integration testing

Five manual integration scenarios were successfully exercised with
GPT-6 Luna during development:

1. Focused policy retrieval.
2. Complete policy edition comparison.
3. Combined audit and policy evidence.
4. Deterministic missing-order handling.
5. Refund-date false-alarm detection.

### Runtime verification

The application and automated tests have been verified locally on Windows using Python 3.10 and inside Docker using Python 3.12.

Both offline auditing and live OpenAI integration were successfully executed inside Docker.

### Evaluation limitations

The audit and retrieval evaluations use small synthetic development fixtures. The retrieval score measures whether the expected policy section is ranked first, not whether every generated answer is correct.

Reference validation reduces unsupported citations but does not verify every factual claim or numerical statement in an LLM response.

Unfamiliar questions, ambiguous wording and provider failures can still result in incomplete or rejected responses.
