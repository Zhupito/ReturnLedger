"""A fresh in-memory ledger for each audit. All date arithmetic runs in SQLite."""

import csv
import re
import sqlite3
from contextlib import closing
from datetime import date

from .policy import DATA, PolicyBook, holiday_floor, window_days

DATES = ("purchased", "delivered", "requested", "refunded")
CALCULATE = """
WITH standard(due) AS (SELECT date(:delivered, '+' || :days || ' days')),
effective(due) AS (SELECT max(due, coalesce(:floor, due)) FROM standard)
SELECT due, cast(julianday(:requested) - julianday(due) AS INTEGER) AS request_delta,
       cast(julianday(:refunded) - julianday(due) AS INTEGER) AS refund_delta
FROM effective
"""


def classify(db, book, order):
    evidence = []
    row = dict(
        order,
        status="review",
        deadline=None,
        days_late=None,
        false_alarm=None,
        evidence=evidence,
        reason="",
    )
    try:
        edition = book.edition_for(order["purchased"])
        row["edition"] = edition
        if order["item_type"] == "custom":
            evidence.append(book.required(edition, "exception").citation)
            raise ValueError("Custom item requires a supervisor decision.")
        if order["item_type"] != "stock":
            raise ValueError("Unknown item type.")
        standard = book.required(edition, "standard")
        holiday = book.required(edition, "holiday")
        evidence.extend([standard.citation, holiday.citation])
        if not all(order[field] for field in DATES):
            raise ValueError("Missing delivery or request date.")
        if sorted(order[f] for f in DATES) != [order[f] for f in DATES]:
            raise ValueError("Order events are out of sequence.")
        days = window_days(standard.text)
        floor = holiday_floor(holiday.text, order["purchased"])
        due, request_delta, refund_delta = db.execute(
            CALCULATE, dict(order, days=days, floor=floor)
        ).fetchone()
        row.update(
            status="late" if request_delta > 0 else "on_time",
            deadline=due,
            days_late=max(0, request_delta),
            false_alarm=request_delta <= 0 < refund_delta,
            reason="Request compared with the inclusive deadline.",
        )
    except ValueError as error:
        row["reason"] = str(error)
    return row


def audit(month, folder=DATA):
    if not isinstance(month, str) or not re.fullmatch(
        r"[0-9]{4}-(0[1-9]|1[0-2])", month
    ):
        raise ValueError("Use a refund month in YYYY-MM format.")
    book = PolicyBook(folder)
    with closing(sqlite3.connect(":memory:")) as db:
        db.row_factory = sqlite3.Row
        db.execute("""CREATE TABLE ledger(order_id TEXT PRIMARY KEY, purchased TEXT,
                   delivered TEXT, item_type TEXT, requested TEXT, refunded TEXT)""")
        with (folder / "ledger.csv").open(newline="", encoding="utf-8") as source:
            for order in csv.DictReader(source):
                for field in DATES:
                    if (
                        order[field]
                        and date.fromisoformat(order[field]).isoformat() != order[field]
                    ):
                        raise ValueError(f"Invalid ISO date in {order['order_id']}.")
                db.execute(
                    "INSERT INTO ledger VALUES (:order_id,:purchased,:delivered,"
                    ":item_type,:requested,:refunded)",
                    order,
                )
        selected = db.execute(
            "SELECT * FROM ledger WHERE substr(refunded,1,7)=? ORDER BY order_id",
            (month,),
        )
        rows = [classify(db, book, dict(o)) for o in selected]
    used = {ref for row in rows for ref in row["evidence"]}
    return {
        "month": month,
        "rows": rows,
        "counts": {
            s: sum(r["status"] == s for r in rows)
            for s in ("late", "on_time", "review")
        },
        "false_alarms": sum(r["false_alarm"] is True for r in rows),
        "sources": {
            c.citation: {"file": c.source, "quote": c.text}
            for c in book.clauses
            if c.citation in used
        },
    }
