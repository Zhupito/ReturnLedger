# Quick start

This guide introduces the main features of ReturnLedger and explains how to run the application locally or inside Docker.

## 1. Run locally

Requirements:

- Python 3.10 or 3.12 (tested versions)
- Git
- A web browser

No external Python dependencies are required.

Clone the repository:

```bash
git clone https://github.com/Zhupito/ReturnLedger.git
cd ReturnLedger
```

Start the application:

```bash
python -m returnledger serve
```

On Windows, you can also use:

```powershell
py -3.10 -m returnledger serve
```

Open http://127.0.0.1:8080 in your browser.

Press Ctrl+C in the terminal to stop the server.

## 2. Explore the application

Select February 2025 as the reporting month.

The dashboard contains 11 fictional orders:

- 3 late requests.
- 4 on-time requests.
- 4 orders requiring manual review.
- 4 refund-date false alarms (a subset of on-time orders).

Try the following:

1. Select a summary card to filter the refund ledger.
2. Inspect NQ-103 to understand refund-date false alarms.
3. Inspect NQ-106 to explore standard and holiday deadlines.
4. Inspect NQ-108 to understand manual-review decisions.
5. Search for `holiday extension` under policy edition `2024-A`.
6. Download the audit report as JSON.

The audit engine and policy search work without an API key.

## 3. Enable the AI assistant (optional)

Create a `.env` file in the repository root:

```dotenv
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-6-luna
```

GPT-6 Luna was used during live integration testing. API access and billing are required.

Do not commit your API key. The `.env` file is excluded from Git.

In Git Bash, load the configuration and start the application:

```bash
set -a
source .env
set +a
python -m returnledger serve
```

On Windows, use `py -3.10` instead of `python` if needed.

The application reads environment variables directly and does not automatically load `.env`.

### Example questions

- Which orders were filed late, and by how many days?
- What is the standard return period under the 2025-A policy?
- Compare the 2024-A and 2025-A policy editions.
- Why was order NQ-999 classified as late?
- Which orders would be falsely flagged using refund dates?

The assistant has three read-only tools:

- `read_audit`: structured audit results.
- `search_policy`: targeted lexical retrieval.
- `read_policy`: complete policy edition retrieval.

The deterministic audit engine remains responsible for all audit decisions.

Live API calls may incur charges.

## 4. Run with Docker

With Docker running, build the image:

```bash
docker build -t returnledger .
```

Run without AI:

```bash
docker run --rm -p 127.0.0.1:8080:8080 returnledger
```

Or run with AI:

```bash
docker run --rm --env-file .env -p 127.0.0.1:8080:8080 returnledger
```

Use unquoted values in `.env` when passing it to Docker.

Open http://127.0.0.1:8080 in your browser.

## 5. Run the tests

```bash
python -m unittest discover -v
python -m returnledger evaluate
```

Recorded verification results:

| Check | Result |
|---|---:|
| Automated tests | 38/38 |
| Audit evaluation | 11/11 |
| Retrieval Top-1 accuracy | 8/8 |

The tests and application have been verified on Windows with Python 3.10 and inside Docker with Python 3.12.

These results apply to the bundled synthetic fixtures, not general LLM accuracy or production performance.

## 6. Further documentation

- [README](README.md) — project overview and application screenshots.
- [Architecture](docs/ARCHITECTURE.md) — system design and technical decisions.
- [Walkthrough](docs/WALKTHROUGH.md) — step-by-step application workflow.
- [Evaluation](docs/EVALUATION.md) — testing methodology and limitations.

ReturnLedger is a local, read-only portfolio application using fictional transaction data and policy documents.
