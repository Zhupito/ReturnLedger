"""Small Chat Completions tool loop. The caller owns the selected reporting month."""

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .policy import PolicyBook


def tool(name, description, properties):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(properties),
                "additionalProperties": False,
            },
        },
    }


def complete(messages, tools):
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        raise ValueError("Set OPENAI_API_KEY to use the live assistant.")
    body = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
    }
    request = Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=35) as response:
            return json.load(response)["choices"][0]["message"]
    except HTTPError as error:
        raise ValueError(
            f"Model service returned HTTP {error.code}. Check model, key and quota."
        ) from error
    except (URLError, TimeoutError, KeyError, IndexError) as error:
        raise ValueError("Model service unavailable or reply incomplete.") from error


def ask(question, report, send=complete):
    if not isinstance(question, str) or not 1 <= len(question.strip()) <= 600:
        raise ValueError("Enter a question of 1–600 characters.")
    book = PolicyBook()
    editions = [e["edition"] for e in book.editions]
    tools = [
        tool(
            "read_audit",
            "Read the selected month's ledger decisions and cited policy.",
            {},
        ),
        tool(
            "search_policy",
            "Find exact policy excerpts in one edition.",
            {
                "query": {"type": "string"},
                "edition": {"type": "string", "enum": editions},
            },
        ),
    ]
    messages = [
        {
            "role": "system",
            "content": f"Discuss fictional North Quay refunds for {report['month']}. "
            "Use read_audit for order/count questions and search_policy for policy questions. "
            "Use only tool evidence. Cite policy as [2025-A#standard] and orders by NQ ID. "
            "Explain uncertainty or absent evidence. The selected month is fixed. "
            "Import warnings list orders excluded from totals across all months. "
            "Never present a reviewed row as a violation.",
        },
        {"role": "user", "content": question},
    ]
    trace, exposed_orders, exposed_refs = [], set(), set()
    for _ in range(4):
        message = send(messages, tools)
        calls = message.get("tool_calls") or []
        if not calls:
            answer = message.get("content") or ""
            refs = set(re.findall(r"\[([^\[\]]+#[^\[\]]+)\]", answer))
            orders = set(re.findall(r"\bNQ-\d+\b", answer))
            if (
                not trace
                or not answer.strip()
                or not refs <= exposed_refs
                or not orders <= exposed_orders
            ):
                raise ValueError(
                    "The reply lacked tool evidence or cited an unknown reference."
                )
            return {"answer": answer, "tools": trace}
        if len(calls) > 4:
            raise ValueError("Too many tool calls.")
        messages.append(
            {
                "role": "assistant",
                "content": message.get("content"),
                "tool_calls": calls,
            }
        )
        for call in calls:
            name = call["function"]["name"]
            args = json.loads(call["function"]["arguments"])
            if name == "read_audit" and args == {}:
                result = report
                exposed_orders.update(r["order_id"] for r in report["rows"])
                exposed_orders.update(
                    w["order_id"] for w in report.get("import_warnings", [])
                )
                exposed_refs.update(report["sources"])
            elif (
                name == "search_policy"
                and isinstance(args, dict)
                and set(args) == {"query", "edition"}
                and args["edition"] in editions
                and isinstance(args["query"], str)
                and 1 <= len(args["query"].strip()) <= 300
            ):
                result = {
                    c.citation: c.text
                    for c in book.search(args["query"], args["edition"])[:3]
                }
                exposed_refs.update(result)
            else:
                raise ValueError(
                    "The model requested an unsupported tool or arguments."
                )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result),
                }
            )
            trace.append({"name": name, "arguments": args})
    raise ValueError("The model exceeded the tool round limit.")
