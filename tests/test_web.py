import io
import json
import unittest
from unittest.mock import patch

from returnledger.assistant import ask
from returnledger.audit import audit
from returnledger.web import app


def request(path, query="", method="GET", body=b""):
    status = []
    env = {
        "PATH_INFO": path,
        "QUERY_STRING": query,
        "REQUEST_METHOD": method,
        "CONTENT_TYPE": "application/json",
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }
    data = b"".join(app(env, lambda code, headers: status.append(code)))
    return status[0], json.loads(data)


class WebTests(unittest.TestCase):
    def test_audit(self):
        status, result = request("/api/audit")
        self.assertEqual(status, "200 OK")
        self.assertEqual(result["false_alarms"], 4)
        self.assertEqual(result["import_warnings"], [])

    def test_edition_search(self):
        status, result = request("/api/search", "edition=2024-A&q=holiday")
        self.assertEqual(status, "200 OK")
        self.assertEqual(next(iter(result)), "2024-A#holiday")

    def test_invalid_request(self):
        self.assertEqual(
            request("/api/ask", method="POST", body=b"{}")[0], "400 Bad Request"
        )
        self.assertEqual(request("/unknown")[0], "404 Not Found")

    def test_model_wire_format(self):
        replies = [
            {
                "tool_calls": [
                    {
                        "id": "a",
                        "type": "function",
                        "function": {"name": "read_audit", "arguments": "{}"},
                    }
                ]
            },
            {"content": "NQ-104 was late."},
        ]

        def transport(req, timeout):
            sent = json.loads(req.data)
            self.assertEqual(req.get_method(), "POST")
            self.assertEqual(len(sent["tools"]), 3)
            self.assertEqual(
                {t["function"]["name"] for t in sent["tools"]},
                {"read_audit", "search_policy", "read_policy"}
            )
            if len(replies) == 1:
                self.assertEqual(sent["messages"][-1]["tool_call_id"], "a")
                self.assertIn("NQ-104", sent["messages"][-1]["content"])
            return io.BytesIO(
                json.dumps({"choices": [{"message": replies.pop(0)}]}).encode()
            )

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-only"}),
            patch("returnledger.assistant.urlopen", transport),
        ):
            result = ask("Which order?", audit("2025-02"))
        self.assertEqual(result["answer"], "NQ-104 was late.")
