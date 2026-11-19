import json
import shutil
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
