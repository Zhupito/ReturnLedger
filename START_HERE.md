# Start here

## 1. Run the demo on Windows

Extract the whole ZIP. Open the **returnledger** folder containing README.md. In File Explorer, click the address bar, type `powershell`, and press Enter. With Python 3.12 installed, run:

```powershell
py -3.12 --version
py -3.12 -m returnledger serve
```

Visit http://127.0.0.1:8080. Leave the terminal open while using the demo. Press Ctrl+C to stop it. If the port is busy, add `--port 8081` and open that port instead. On macOS/Linux, use `python3` instead of `py -3.12`.

## 2. Take a two-minute tour

1. Leave the month on February 2025. Locate the three late requests.
2. Filter to **Refund-date false alarms**. Open NQ-103 and compare requested, refunded and deadline.
3. Switch to **Manual review** and open NQ-108. Its missing request date leaves no way to measure lateness.
4. Search for **holiday** under each edition. Read both returned clauses.
5. Download the JSON. Each row has its decision, dates, reason and policy references. The sources object resolves each reference to a quote and filename.

## 3. Try a live RAG question (optional)

The live assistant uses OpenAI Chat Completions. Use an API key with API billing and access to a tool-capable model. Stop the server, then run in PowerShell:

```powershell
$secret = Read-Host "OpenAI API key" -AsSecureString
$env:OPENAI_API_KEY = [System.Net.NetworkCredential]::new('', $secret).Password
$env:OPENAI_MODEL = "gpt-4o-mini"
py -3.12 -m returnledger serve
```

Ask “Which February orders were one day late? Show the order IDs.” Compare the answer with the three ledger rows. For a policy-only example try “How did the holiday extension change between the two editions?” Calls incur provider charges. The selected month stays fixed until you change it in the interface. After stopping the server, clear the key with `Remove-Item Env:OPENAI_API_KEY`. The app reads environment variables directly.

## 4. Run the checks

```powershell
py -3.12 -m unittest discover -v
py -3.12 -m returnledger evaluate
```

For an optional local container, run `docker build -t returnledger .` then `docker run --rm -p 127.0.0.1:8080:8080 returnledger`. The bundled server is intended for a local, single-user demo.

Read [the walkthrough](docs/WALKTHROUGH.md) for a step-by-step explanation of the application and [the architecture documentation](docs/ARCHITECTURE.md) for technical design details.
