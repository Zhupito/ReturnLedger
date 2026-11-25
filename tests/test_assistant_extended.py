"""Regression tests for full-policy retrieval and missing-order handling.

The injected send function stands in for the LLM. No API key or network
connection is needed. The audit and policy loaders use the project's fixtures.
"""

import json
import unittest
from copy import deepcopy
from unittest.mock import Mock

from returnledger.assistant import ask
from returnledger.audit import audit
from returnledger.policy import PolicyBook


SECTIONS = ("standard", "holiday", "exception", "payment")


def tool_call(name, arguments, call_id="call-1"):
    """Build a tool request in the Chat Completions message format."""
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


class ExtendedAssistantTests(unittest.TestCase):
    def setUp(self):
        self.report = audit("2025-02")
        self.book = PolicyBook()

    def scripted_sender(self, *replies):
        """Capture independent snapshots of each simulated API request."""
        history = []
        responses = iter(replies)

        def reply(messages, tools):
            history.append((deepcopy(messages), deepcopy(tools)))
            return next(responses)

        return Mock(side_effect=reply), history

    def expected_policy(self, edition):
        return {
            f"{edition}#{section}": self.book.required(edition, section).text
            for section in SECTIONS
        }

    def test_read_policy_tool_schema(self):
        send, history = self.scripted_sender(
            {"tool_calls": [tool_call("read_policy", {"edition": "2024-A"})]},
            {"content": "See [2024-A#standard]."},
        )
        ask("Summarize the 2024 policy.", self.report, send=send)
        tools = {item["function"]["name"]: item for item in history[0][1]}
        self.assertEqual(set(tools), {"read_audit", "search_policy", "read_policy"})
        schema = tools["read_policy"]["function"]["parameters"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(schema["required"], ["edition"])
        self.assertEqual(set(schema["properties"]), {"edition"})
        self.assertEqual(schema["properties"]["edition"]["type"], "string")
        self.assertCountEqual(schema["properties"]["edition"]["enum"],
                              ["2024-A", "2025-A"])
        self.assertIs(schema["additionalProperties"], False)

    def test_read_policy_returns_all_four_sections(self):
        for edition in ("2024-A", "2025-A"):
            with self.subTest(edition=edition):
                send, history = self.scripted_sender(
                    {"tool_calls": [tool_call("read_policy", {"edition": edition})]},
                    {"content": " ".join(f"[{edition}#{s}]" for s in SECTIONS)},
                )
                result = ask("Summarize the policy.", self.report, send=send)
                evidence = json.loads(history[1][0][-1]["content"])
                self.assertEqual(evidence, self.expected_policy(edition))
                self.assertEqual(result["tools"], [
                    {"name": "read_policy", "arguments": {"edition": edition}}
                ])
                self.assertEqual(send.call_count, 2)

    def test_compare_two_editions_with_two_tool_calls(self):
        calls = [
            tool_call("read_policy", {"edition": "2024-A"}, "call-2024"),
            tool_call("read_policy", {"edition": "2025-A"}, "call-2025"),
        ]
        answer = " ".join(
            f"[{edition}#{section}]"
            for edition in ("2024-A", "2025-A") for section in SECTIONS
        )
        send, history = self.scripted_sender({"tool_calls": calls}, {"content": answer})
        result = ask("Compare both policy editions.", self.report, send=send)
        self.assertEqual(result["answer"], answer)
        self.assertEqual(result["tools"], [
            {"name": "read_policy", "arguments": {"edition": "2024-A"}},
            {"name": "read_policy", "arguments": {"edition": "2025-A"}},
        ])
        tool_messages = [m for m in history[1][0] if m["role"] == "tool"]
        self.assertEqual(len(tool_messages), 2)
        self.assertEqual([m["tool_call_id"] for m in tool_messages],
                         ["call-2024", "call-2025"])
        for edition, message in zip(("2024-A", "2025-A"), tool_messages):
            self.assertEqual(json.loads(message["content"]), self.expected_policy(edition))
        self.assertEqual(send.call_count, 2)

    def test_read_policy_rejects_invalid_arguments(self):
        invalid = ({}, {"edition": "2099-A"}, {"edition": None},
                   {"edition": ["2024-A"]}, {"edition": "2024-A", "query": "all"},
                   ["2024-A"])
        for arguments in invalid:
            with self.subTest(arguments=arguments):
                send, _ = self.scripted_sender(
                    {"tool_calls": [tool_call("read_policy", arguments)]}
                )
                with self.assertRaisesRegex(ValueError, "unsupported tool or arguments"):
                    ask("Read the policy.", self.report, send=send)
                self.assertEqual(send.call_count, 1)

    def test_read_policy_rejects_unretrieved_citations(self):
        for citation in ("2025-A#standard", "2024-A#invented"):
            with self.subTest(citation=citation):
                send, _ = self.scripted_sender(
                    {"tool_calls": [tool_call("read_policy", {"edition": "2024-A"})]},
                    {"content": f"See [{citation}]."},
                )
                with self.assertRaisesRegex(ValueError, "unknown reference"):
                    ask("Read the 2024 policy.", self.report, send=send)

    def test_read_policy_does_not_expose_order_ids(self):
        send, _ = self.scripted_sender(
            {"tool_calls": [tool_call("read_policy", {"edition": "2025-A"})]},
            {"content": "NQ-103 was on time."},
        )
        with self.assertRaisesRegex(ValueError, "unknown reference"):
            ask("Summarize the policy.", self.report, send=send)

    def test_missing_order_returns_without_model_call(self):
        send = Mock(side_effect=AssertionError("Missing order must not invoke the LLM"))
        result = ask("Why was order NQ-999 classified as late?", self.report, send=send)
        self.assertEqual(result["tools"], [])
        self.assertIn("NQ-999", result["answer"])
        self.assertIn("not found", result["answer"])
        self.assertIn("2025-02", result["answer"])
        self.assertIn("cannot be determined", result["answer"])
        send.assert_not_called()

    def test_missing_order_handles_lowercase_id(self):
        send = Mock(side_effect=AssertionError("Unexpected LLM call"))
        result = ask("What happened to nq-999?", self.report, send=send)
        self.assertIn("NQ-999", result["answer"])
        self.assertIn("not found", result["answer"])
        self.assertEqual(result["tools"], [])
        send.assert_not_called()

    def test_order_outside_selected_month(self):
        # NQ-112 exists in the ledger but was refunded in March, not February.
        self.assertIn("NQ-112", {row["order_id"] for row in audit("2025-03")["rows"]})
        send = Mock(side_effect=AssertionError("Unexpected LLM call"))
        result = ask("Was NQ-112 late?", self.report, send=send)
        self.assertIn("not found in the audit for 2025-02", result["answer"])
        self.assertEqual(result["tools"], [])
        send.assert_not_called()

    def test_known_order_still_uses_model_and_audit(self):
        send, _ = self.scripted_sender(
            {"tool_calls": [tool_call("read_audit", {})]},
            {"content": "NQ-103 was on time."},
        )
        result = ask("Why was NQ-103 on time?", self.report, send=send)
        self.assertEqual(result["answer"], "NQ-103 was on time.")
        self.assertEqual(result["tools"], [{"name": "read_audit", "arguments": {}}])
        self.assertEqual(send.call_count, 2)

    def test_import_warning_order_is_not_treated_as_missing(self):
        warning = {"order_id": "NQ-112", "field": "refunded",
                   "raw_value": "2025-03-32", "reason": "Invalid calendar date."}
        self.report["import_warnings"].append(warning)
        send, history = self.scripted_sender(
            {"tool_calls": [tool_call("read_audit", {})]},
            {"content": "NQ-112 was excluded because of an invalid refund date."},
        )
        result = ask("What happened to NQ-112?", self.report, send=send)
        self.assertIn("NQ-112 was excluded", result["answer"])
        evidence = json.loads(history[1][0][-1]["content"])
        self.assertIn(warning, evidence["import_warnings"])
        self.assertEqual(send.call_count, 2)

    def test_multiple_ids_keep_normal_workflow(self):
        # Current pre-validation intentionally handles just one distinct ID.
        send, _ = self.scripted_sender(
            {"tool_calls": [tool_call("read_audit", {})]},
            {"content": "NQ-103 was on time. The other requested order was not found."},
        )
        result = ask("Compare NQ-103 and NQ-999.", self.report, send=send)
        self.assertIn("NQ-103 was on time", result["answer"])
        self.assertEqual(result["tools"], [{"name": "read_audit", "arguments": {}}])
        self.assertEqual(send.call_count, 2)


if __name__ == "__main__":
    unittest.main()
