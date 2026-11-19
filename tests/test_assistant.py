import json
import unittest
from unittest.mock import patch

from returnledger.assistant import ask
from returnledger.audit import audit


def call(name, args):
    return {
        "tool_calls": [
            {
                "id": "call-1",
                "type": "function",
                "function": {"name": name, "arguments": json.dumps(args)},
            }
        ]
    }


class AssistantTests(unittest.TestCase):
    def setUp(self):
        self.report = audit("2025-02")

    def run_script(self, *steps):
        messages_seen = []

        def send(messages, tools):
            messages_seen.append(list(messages))
            return steps[len(messages_seen) - 1]

        return ask("Which returns were late?", self.report, send), messages_seen

    def test_both_tools(self):
        answer, history = self.run_script(
            call("search_policy", {"edition": "2025-A", "query": "holiday"}),
            call("read_audit", {}),
            {"content": "NQ-104 was one day late [2025-A#standard]."},
        )
        self.assertEqual(len(answer["tools"]), 2)
        self.assertIn("2025-A#holiday", history[1][-1]["content"])
        self.assertIn("NQ-104", history[2][-1]["content"])

    def test_unknown_citation(self):
        with self.assertRaises(ValueError):
            self.run_script(
                call("read_audit", {}), {"content": "NQ-999 [2026-A#standard]"}
            )

    def test_cannot_read_unexposed_order(self):
        with self.assertRaises(ValueError):
            self.run_script(
                call("search_policy", {"edition": "2024-A", "query": "custom"}),
                {"content": "NQ-107 needs review."},
            )

    def test_unsupported_tool_or_argument(self):
        for request in (call("run_sql", {}), call("read_audit", {"month": "1999-04"})):
            with self.subTest(request=request), self.assertRaises(ValueError):
                self.run_script(request)

    def test_round_limit(self):
        with self.assertRaisesRegex(ValueError, "round limit"):
            self.run_script(*[call("read_audit", {})] * 4)

    def test_no_tool(self):
        with self.assertRaises(ValueError):
            self.run_script({"content": "Because I say so."})

    def test_no_key(self):
        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": ""}),
            self.assertRaisesRegex(ValueError, "API_KEY"),
        ):
            ask("question", self.report)
