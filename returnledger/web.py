"""Local demo server with three JSON endpoints."""

import json
from pathlib import Path
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from .assistant import ask
from .audit import audit
from .policy import PolicyBook

STATIC = Path(__file__).with_name("static")
ASSETS = {
    "/": ("index.html", "text/html"),
    "/app.js": ("app.js", "text/javascript"),
    "/style.css": ("style.css", "text/css"),
}


def app(env, start_response):
    path = env["PATH_INFO"]
    method = env["REQUEST_METHOD"]
    params = parse_qs(env.get("QUERY_STRING", ""))
    month = params.get("month", ["2025-02"])[0]
    status, mime = "200 OK", "application/json"
    try:
        if path in ASSETS and method == "GET":
            filename, mime = ASSETS[path]
            data = (STATIC / filename).read_bytes()
        elif path == "/api/audit" and method == "GET":
            data = json.dumps(audit(month)).encode()
        elif path == "/api/search" and method == "GET":
            book = PolicyBook()
            edition = params.get("edition", ["2025-A"])[0]
            if edition not in {e["edition"] for e in book.editions}:
                raise ValueError("Unknown edition.")
            clauses = book.search(params.get("q", [""])[0], edition)
            data = json.dumps({c.citation: c.text for c in clauses}).encode()
        elif path == "/api/ask" and method == "POST":
            if env.get("CONTENT_TYPE", "").split(";")[0] != "application/json":
                raise ValueError("Expected JSON.")
            length = int(env.get("CONTENT_LENGTH") or 0)
            if not 1 <= length <= 4096:
                raise ValueError("Invalid request size.")
            body = json.loads(env["wsgi.input"].read(length))
            result = ask(body["question"], audit(month))
            data = json.dumps(result).encode()
        else:
            status, data = "404 Not Found", b'{"error":"Unknown endpoint or method."}'
    except (ValueError, KeyError, TypeError) as error:
        status, data = "400 Bad Request", json.dumps({"error": str(error)}).encode()
    start_response(
        status,
        [("Content-Type", mime + "; charset=utf-8"), ("Cache-Control", "no-store")],
    )
    return [data]


def serve(host, port):
    with make_server(host, port, app) as server:
        print(f"ReturnLedger is listening at http://{host}:{port}", flush=True)
        server.serve_forever()
