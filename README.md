# Workshop - How Systems Talk in Real Time

> Polling · Webhooks · SSE · WebSockets - and how they show up in modern AI apps.

This is a complete, hands-on workshop kit. It contains:

```
realtime/
├── concepts/        ← 7 deep-dive markdown docs (read these first)
├── diagrams/        ← 14 draw.io diagrams (open in app.diagrams.net or VS Code drawio extension)
├── examples/        ← 7 self-contained client/server folders, one per topic, run from terminal
│   ├── 01_http_basics/        ← port 8101
│   ├── 02_short_polling/      ← port 8102
│   ├── 03_long_polling/       ← port 8103
│   ├── 04_webhooks/           ← port 8104
│   ├── 05_sse/                ← port 8105
│   ├── 06_websockets/         ← port 8106
│   ├── 07_openai_streaming/   ← no server; talks to OpenAI directly
│   └── qa.sh                  ← automated end-to-end test of all 7 examples + both projects
├── projects/
│   ├── project_1_streaming_chat/      ← chat UI showing polling vs SSE vs WS side-by-side
│   └── project_2_webhook_dashboard/   ← webhook intake + live SSE dashboard
└── .env             ← OpenAI / Supabase / MongoDB keys (pre-populated)
```

## Quick start

```bash
cd realtime
source .venv/bin/activate           # already created with deps installed

# (Optional) Re-install deps if needed
uv pip install fastapi 'uvicorn[standard]' httpx websockets python-dotenv openai

# Run an example - each has a README with two-terminal commands.
# e.g. example 01:
#   Terminal 1: cd examples/01_http_basics && uvicorn server:app --port 8101
#   Terminal 2: cd examples/01_http_basics && python client.py

# Run all examples + both projects end-to-end (smoke test):
cd examples && bash qa.sh

# Run Project 1 (chat app)
cd projects/project_1_streaming_chat && uvicorn server:app --reload --port 8000
# → open http://localhost:8000

# Run Project 2 (webhook dashboard) - in a separate terminal
cd projects/project_2_webhook_dashboard && uvicorn server:app --reload --port 9000
# → open http://localhost:9000
```

---

## Recommended teaching order

A **60-90 minute** session works like this:

| Time | Block | What you do | Materials |
|------|-------|------------|-----------|
| 5 min | Opener | "Every real-time feature you've seen is one of 4 patterns" - set the stage with `00_overview.md` | `concepts/00_overview.md` |
| 8 min | HTTP foundation | Establish request/response baseline. Why server can't push. | `01_http_fundamentals.md` + `diagrams/01_http_basic.drawio` |
| 8 min | Polling | Show short polling timeline, then long polling. Walk through trade-offs. | `02_polling.md` + diagrams `02`, `03`, `04` |
| 8 min | Webhooks | Inversion. Signature verification, dedup, retries. | `03_webhooks.md` + diagrams `05`, `06`, `07` |
| 8 min | SSE | Wire format, EventSource, Last-Event-ID resume. | `04_sse.md` + diagrams `08`, `09` |
| 8 min | WebSockets | Handshake, full duplex, scaling. | `05_websockets.md` + diagrams `10`, `11` |
| 5 min | Decision matrix | "When to use what" - the cheat sheet. | `06_decision_matrix.md` + `diagrams/12_decision_matrix.drawio` |
| 5 min | AI & MCP | Where these patterns hide in modern AI stacks. | `07_ai_agents_mcp.md` + `diagrams/13`, `14` |
| 15 min | EXAMPLES live demo | Open two terminal panes. For each topic, start `server.py` on left, run `client.py` on right. Walk through 01→07 in order. | `examples/0*/` |
| 15 min | PROJECT 1 demo | Side-by-side chat. Make the UX cost of each pattern obvious. | `projects/project_1_streaming_chat/` |
| 10 min | PROJECT 2 demo | Webhook → dashboard pipeline. Show dedup, forgery rejection, live push. | `projects/project_2_webhook_dashboard/` |
| 5 min | Q&A | Map participants' own use cases to the right pattern. | - |

---

## How to use each piece

### Concept docs (`concepts/`)

Read in order. Each doc is self-contained but builds on the previous one. They are written to be **read**, not just skimmed - every section has examples, anti-patterns, and "why this matters" callouts.

### Diagrams (`diagrams/`)

Built as **small focused diagrams** that you can show one at a time. The numbering is the teaching order. Open each one full-screen as you reach the matching concept.

Diagrams 13-14 are the "merge" diagrams - they show how all four patterns coexist in a real AI app and how MCP uses SSE.

Open with one of:
- **VS Code:** install the `hediet.vscode-drawio` extension, then open the `.drawio` file
- **Web:** drag the file into [app.diagrams.net](https://app.diagrams.net)

### Examples (`examples/`)

Seven self-contained folders, one per topic. Each has a `server.py` (if applicable), a `client.py`, and a `README.md` with **exact two-terminal commands** (`uvicorn server:app --port N` on the left, `python client.py` on the right).

This is the primary teaching surface - open `examples/02_short_polling/` and you can read the server, read the client, run them together, and see the pattern come alive.

To verify everything works end-to-end:
```bash
cd examples && bash qa.sh
```
This starts each server, runs the matching client, asserts expected output, and reports pass/fail for all examples + both projects.

### Project 1 - Streaming Chat (`projects/project_1_streaming_chat/`)

The **same** LLM chat feature exposed three ways:
- Polling (`POST /api/polling/start` then poll status)
- SSE (`POST /api/sse/chat` returns event-stream)
- WebSocket (`WS /api/ws/chat`, supports mid-stream interrupt)

Use this to make the UX cost of each pattern **visceral** - students see the polling card sit empty for 5 seconds while SSE pours words out instantly.

### Project 2 - Webhook Dashboard (`projects/project_2_webhook_dashboard/`)

A complete event pipeline:
- External services POST signed events to `/webhook/payment`
- Backend verifies HMAC, dedups by event ID, stores in SQLite
- Two dashboards compare polling vs SSE for the **receiving** side

Built-in simulators let you demo without ngrok/Stripe:
- "+1 event" / "+5 events" - fire properly signed events
- "Send duplicate" - proves idempotency works
- "Send unsigned" - proves signature check works

---

## Talking points for instructors

These are the moments to drive home:

1. **HTTP is the floor.** Everything else is a workaround for "server can't push."
2. **Polling isn't shameful.** Sometimes it's the right answer (low frequency, simple).
3. **Webhooks aren't "fire and forget."** Without signature verification + dedup, they're a security and correctness disaster.
4. **SSE is criminally underused.** Most teams reach for WebSocket when SSE would do.
5. **WebSocket overhead is real.** 100k idle WebSockets cost 10-20 GB of RAM. Don't pay it unless you need bidirectional.
6. **A real app composes all four.** Show diagram `13_ai_app_all_patterns` - point out the four patterns coexisting.
7. **MCP is built on SSE.** Most students don't know this. Show diagram `14_mcp_architecture`.

---

## Troubleshooting

- **Server already on that port:** an earlier example didn't shut down. `pkill -f uvicorn` clears it.
- **OpenAI example fails:** check `.env` has `OPENAI_API_KEY` set.
- **Project 1 / 2 port conflict:** they use 8000 and 9000 respectively. If something else has those ports, pass `--port XXXX` to uvicorn.
- **Browser can't reach localhost server:** check the server logs in your terminal, look for `Uvicorn running on http://127.0.0.1:XXXX`.

---

## What this workshop is NOT trying to cover

- The full WebSocket RFC (frame layout, masking) - covered conceptually but not at the byte level
- Push notifications (APNs, FCM) - different infrastructure, not in scope
- gRPC streaming - adjacent topic, mention in passing
- HTTP/3 specifics - patterns are the same, transport differs

If a participant asks about any of those, point them at the relevant standards and move on.
