import argparse
import json

from .audit import audit


def main():
    parser = argparse.ArgumentParser(description="Audit fictional North Quay refunds")
    parser.add_argument(
        "action", choices=["serve", "audit", "evaluate"], nargs="?", default="serve"
    )
    parser.add_argument("--month", default="2025-02")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    if args.action == "serve":
        from .web import serve

        serve(args.host, args.port)
    elif args.action == "evaluate":
        from .evaluate import evaluate

        result = evaluate()
        print(json.dumps(result, indent=2))
        if any(x["passed"] != x["total"] for x in result.values()):
            raise SystemExit(1)
    else:
        print(json.dumps(audit(args.month), indent=2))


if __name__ == "__main__":
    main()
