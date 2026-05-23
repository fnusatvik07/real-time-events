# Project 1: Streaming AI Chat - Polling vs SSE vs WebSocket

A single FastAPI app that exposes the **same LLM chat feature** through **three different real-time patterns**, side by side, so you can *feel* the difference.

## Run it

```bash
# from repo root
source .venv/bin/activate
cd projects/project_1_streaming_chat
uvicorn server:app --reload --port 8000
```

Open http://localhost:8000

> Reads `OPENAI_API_KEY` from `../../.env`.

## What you'll see

Three cards side by side. Type the same prompt in each and hit run:

| Card | What happens visually | What's going on |
|------|---------------------|-----------------|
| **POLLING** | Spinner → wait → BLAM, full answer appears | UI fires `POST /api/polling/start`, then `GET /api/polling/status/{id}` every 1s, then `GET /api/polling/result/{id}` once done |
| **SSE** | Words pour in as they're generated | UI streams `POST /api/sse/chat`, parses `event: token` messages from the body |
| **WS** | Words stream + you can interrupt mid-answer | UI opens one `WS /api/ws/chat`, sends `{type:"prompt"}`, receives `{type:"token"}` messages, can send `{type:"interrupt"}` |

The metrics row (status, first-byte latency, total time, tokens received) makes the UX cost of each pattern obvious.

## Endpoint cheat sheet

```
POST /api/polling/start          {prompt}      -> {job_id}
GET  /api/polling/status/{id}                  -> {status, elapsed_ms}
GET  /api/polling/result/{id}                  -> {result}

POST /api/sse/chat               {prompt}      -> text/event-stream
                                                  event: open
                                                  event: token data: ...
                                                  event: done

WS   /api/ws/chat               <- {type:"prompt", text:"..."}
                                 -> {type:"token", text:"..."}
                                 -> {type:"done"}
                                <- {type:"interrupt"}
                                 -> {type:"interrupted"}
```

## Things to demo live

1. **Run polling first.** Highlight the dead time and the "all at once" reveal.
2. **Run SSE.** Same prompt, but words flow. Watch the *first-byte* metric drop from "several seconds" to "under a second."
3. **Run WS with a long prompt.** Click **Interrupt** mid-answer. Note polling/SSE can't do this - the request is already in flight.
4. **Open DevTools → Network.** Show:
   - Polling: many short requests
   - SSE: one long request, EventStream tab shows individual messages
   - WS: one upgraded connection, Messages tab shows frames

## Code walk

`server.py` is broken into three labeled sections (Polling, SSE, WebSocket). Each is small enough to read top-to-bottom in a few minutes. Show students how each section is just *the same `openai` call wrapped in a different delivery mechanism*.

The frontend (`static/index.html`) deliberately keeps the three cards visually parallel so the **only** thing that differs is what arrives, when.
