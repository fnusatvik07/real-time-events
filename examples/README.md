# Hands-on Examples

Seven self-contained examples - one per topic. Each is a folder with a `server.py` (where applicable), a `client.py`, and a `README.md` with **exact terminal commands**.

The intent is that you sit at a terminal with two panes open. Read the topic's concept doc, then run the example: start the server on the left, run the client on the right, watch what happens.

## Order

| # | Folder | Port | What it shows |
|---|--------|------|--------------|
| 01 | `01_http_basics` | 8101 | Plain HTTP request/response - the baseline |
| 02 | `02_short_polling` | 8102 | Client polls every 1s; counter bumps every 5s. Visible waste. |
| 03 | `03_long_polling` | 8103 | Server holds the request until data is ready |
| 04 | `04_webhooks` | 8104 | Receiver + signed sender + dedup test + forgery rejection |
| 05 | `05_sse` | 8105 | Server-Sent Events: 10 events over one open HTTP connection |
| 06 | `06_websockets` | 8106 | Full-duplex echo+broadcast - run 2 clients to see broadcast |
| 07 | `07_openai_streaming` | (none) | Real OpenAI streaming - confirms it IS SSE |

## Run everything

```bash
source ../.venv/bin/activate

# pick any example, follow its README
cd examples/01_http_basics
# (Terminal 1) uvicorn server:app --port 8101
# (Terminal 2) python client.py
```

## Automated QA

To verify all 7 examples (plus both projects) work end-to-end without opening terminals manually:

```bash
cd examples
bash qa.sh
```

This starts each server in the background, runs the matching client, asserts expected behavior, and prints a pass/fail report.
