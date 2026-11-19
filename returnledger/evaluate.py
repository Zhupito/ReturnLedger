"""Small, deterministic regression fixtures. No model calls."""

import csv
import json

from .audit import audit
from .policy import DATA, PolicyBook


def summarize(checks):
    return {
        "total": len(checks),
        "passed": sum(checks.values()),
        "failed": [name for name, passed in checks.items() if not passed],
    }


def evaluate():
    rows = {r["order_id"]: r for r in audit("2025-02")["rows"]}
    with (DATA / "expected.csv").open(newline="") as source:
        expected = {r["order_id"]: r for r in csv.DictReader(source)}
    decisions = {}
    for key in sorted(rows.keys() | expected.keys()):
        if key not in rows or key not in expected:
            decisions[key] = False
            continue
        actual, gold = rows[key], expected[key]
        wanted = (
            gold["status"],
            gold["deadline"] or None,
            int(gold["days_late"]) if gold["days_late"] else None,
            bool(int(gold["false_alarm"])) if gold["false_alarm"] else None,
        )
        decisions[key] = (
            tuple(actual[k] for k in ("status", "deadline", "days_late", "false_alarm"))
            == wanted
        )
    rankings = {}
    book = PolicyBook()
    for edition, question, section in json.loads(
        (DATA / "retrieval_checks.json").read_text()
    ):
        hits = book.search(question, edition)
        rankings[f"{edition} / {question}"] = bool(hits and hits[0].section == section)
    return {
        "ledger_cases": summarize(decisions),
        "retrieval_top_1": summarize(rankings),
    }
