import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from returnledger.audit import audit
from returnledger.evaluate import evaluate
from returnledger.policy import DATA, PolicyBook


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / "data"
        shutil.copytree(DATA, self.folder)

    def replace(self, name, old, new):
        path = self.folder / name
        contents = path.read_text(encoding="utf-8")
        self.assertIn(old, contents)
        path.write_text(contents.replace(old, new), encoding="utf-8")

    def case(self, key):
        return next(
            r for r in audit("2025-02", self.folder)["rows"] if r["order_id"] == key
        )

    def test_gold_cases_and_search(self):
        for result in evaluate().values():
            self.assertEqual(result["failed"], [])

    def test_half_open_month(self):
        self.assertEqual([r["order_id"] for r in audit("2025-03")["rows"]], ["NQ-112"])
        self.assertEqual([r["order_id"] for r in audit("2025-01")["rows"]], ["NQ-113"])
        self.assertEqual(audit("2025-04")["rows"], [])

    def test_invalid_march_refund_keeps_february_audit(self):
        clean = audit("2025-02", self.folder)
        self.replace("ledger.csv", "2025-02-14,2025-03-01", "2025-02-14,2025-03-32")

        report = audit("2025-02", self.folder)

        self.assertEqual(len(report["rows"]), 11)
        self.assertEqual(report["counts"], {"late": 3, "on_time": 4, "review": 4})
        for key in ("rows", "sources", "false_alarms"):
            self.assertEqual(report[key], clean[key], key)
        self.assertEqual(len(report["import_warnings"]), 1)
        warning = report["import_warnings"][0]
        self.assertEqual(warning["order_id"], "NQ-112")
        self.assertEqual(warning["field"], "refunded")
        self.assertEqual(warning["raw_value"], "2025-03-32")
        self.assertIn("YYYY-MM-DD", warning["reason"])

    def test_each_bad_field_is_reported_but_each_order_is_excluded_once(self):
        self.replace(
            "ledger.csv", "NQ-101,2024-12-15,2024-12-20", "NQ-101,20241215,2024-12-32"
        )
        self.replace("ledger.csv", "2025-02-13,2025-02-28", "2025-02-29,2025-02-28")

        february = audit("2025-02", self.folder)
        warnings = february["import_warnings"]
        self.assertEqual(
            [(w["order_id"], w["field"], w["raw_value"]) for w in warnings],
            [
                ("NQ-101", "purchased", "20241215"),
                ("NQ-101", "delivered", "2024-12-32"),
                ("NQ-111", "requested", "2025-02-29"),
            ],
        )
        orders = {r["order_id"] for r in february["rows"]}
        self.assertTrue(orders.isdisjoint({"NQ-101", "NQ-111"}))
        self.assertEqual(len(orders), 9)
        self.assertEqual(february["counts"], {"late": 2, "on_time": 3, "review": 4})
        april = audit("2025-04", self.folder)
        self.assertEqual(april["rows"], [])
        self.assertEqual(april["import_warnings"], warnings)

    def test_leap_day_and_blank_dates_do_not_raise_import_warnings(self):
        self.replace("ledger.csv", "NQ-101,2024-12-15", "NQ-101,2024-02-29")
        report = audit("2025-02", self.folder)
        rows = {r["order_id"]: r for r in report["rows"]}

        self.assertEqual(report["import_warnings"], [])
        self.assertEqual(rows["NQ-101"]["purchased"], "2024-02-29")
        self.assertEqual(rows["NQ-108"]["status"], "review")  # Blank request
        self.assertEqual(rows["NQ-109"]["status"], "review")  # Blank delivery
        self.assertNotIn("NQ-114", rows)  # No posted refund

    def test_cli_restores_march_order_after_correction(self):
        root = self.folder.parent
        shutil.copytree(
            DATA.parent / "returnledger",
            root / "returnledger",
            ignore=shutil.ignore_patterns("__pycache__"),
        )
        command = [sys.executable, "-m", "returnledger", "audit", "--month", "2025-03"]
        self.replace("ledger.csv", "2025-02-14,2025-03-01", "2025-02-14,2025-03-32")
        damaged = json.loads(subprocess.check_output(command, cwd=root))
        self.assertEqual(damaged["rows"], [])
        self.assertEqual([w["order_id"] for w in damaged["import_warnings"]], ["NQ-112"])

        self.replace("ledger.csv", "2025-02-14,2025-03-32", "2025-02-14,2025-03-01")
        repaired = json.loads(subprocess.check_output(command, cwd=root))
        self.assertEqual([r["order_id"] for r in repaired["rows"]], ["NQ-112"])
        self.assertEqual(repaired["import_warnings"], [])

    def test_changed_prose_changes_decision(self):
        self.replace("2025-A.md", "21 calendar days", "24 calendar days")
        self.assertEqual(self.case("NQ-104")["status"], "on_time")

    def test_unknown_wording_abstains(self):
        self.replace("2025-A.md", "21 calendar days", "three working weeks")
        self.assertEqual(self.case("NQ-103")["status"], "review")

    def test_duplicate_holiday_abstains(self):
        self.replace(
            "2024-A.md", "## payment", "## holiday\nA second window.\n\n## payment"
        )
        self.assertEqual(self.case("NQ-101")["status"], "review")

    def test_overlapping_editions_abstain(self):
        self.replace("editions.json", '"until":"2025-01-01"', '"until":"2025-02-01"')
        self.assertEqual(self.case("NQ-103")["status"], "review")

    def test_bad_chronology(self):
        self.replace(
            "ledger.csv", "stock,2025-01-31,2025-02-07", "stock,2025-02-08,2025-02-07"
        )
        self.assertIn("sequence", self.case("NQ-103")["reason"])

    def test_wrong_month_input(self):
        for value in ("2025-00", "", "Feb", "2025-02-01"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                audit(value)

    def test_empty_search(self):
        self.assertEqual(PolicyBook().search("glacier", "2024-A"), [])

    def test_repeatable(self):
        self.assertEqual(json.dumps(audit("2025-02")), json.dumps(audit("2025-02")))
