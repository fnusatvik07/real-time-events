# 05 - Server-Sent Events (ChatGPT-style token streaming)

Realistic scenario: a chat UI sends a prompt; the server streams the answer back one word at a time so the response appears like someone typing. This is exactly what ChatGPT, Claude.ai, Cursor, and every modern LLM chat UI does.

For this example the server uses a **canned** answer (so the demo is deterministic). Example 07 swaps in a real OpenAI call - the wire format is identical.

## What the server does

`POST /chat` with `{"prompt": "..."}`:
- Returns `Content-Type: text/event-stream`
- Yields one event per word (~80ms apart) using the SSE format:
  ```
  id: 7
  event: token
  data: {"text": "Vada", "index": 7}

  ```
- Sends `event: open` first and `event: done` last so the client knows the boundaries

## Run

**Terminal 1:**
```bash
cd examples/05_sse
uvicorn server:app --port 8105
```

**Terminal 2:**
```bash
cd examples/05_sse
python client.py
```

## What you'll see

First the raw wire format for the opening events (so the class can see what an SSE event actually looks like):

```
  'event: open'
  'data: {"prompt": "What are 3 must-try Mumbai street foods?"}'
  ''
  'id: 0'
  'event: token'
  'data: {"text": "Great ", "index": 0}'
  ''
  'id: 1'
  'event: token'
  'data: {"text": "question! ", "index": 1}'
  ''
  ...
```

Then the assembled response (built up word by word from those events):

```
  Great question! Here are 3 must-try Mumbai street foods you can't miss.
  First, Vada Pav - the iconic Mumbai burger: a spiced potato fritter
  inside a soft pav bun, served with green chutney and a fried chili.
  Second, Pav Bhaji - ...
```

And finally a stats summary (token count, time to first token, total stream time).

## Talking points

- **Each blank line separates one event.** Forget the blank line and the client hangs forever waiting for the event to "finish".
- **`id:` fields enable resume.** If the connection drops, the browser sends `Last-Event-ID: <last>` on reconnect and the server resumes from there. This is built into `EventSource`.
- **In the browser the client is two lines.** `new EventSource('/chat')` + `addEventListener('token', ...)`. No library, no reconnection code, no parsing.
- **This IS what OpenAI does.** When you set `stream=True`, OpenAI returns exactly this shape. The `openai` SDK is an SSE parser with JSON-on-top.

## Try it from curl

```bash
curl -N -X POST http://127.0.0.1:8105/chat \
  -H "content-type: application/json" \
  -d '{"prompt":"hello"}'
```

`-N` disables curl's buffering so you can watch the events arrive in real-time. This is the SSE wire format you'd see staring at any LLM provider's streaming API.

## Where this pattern shows up

- OpenAI Chat Completions (`stream=True`)
- Anthropic Messages API (streaming)
- Vercel AI SDK `useChat` hook
- MCP Streamable HTTP transport
- GitHub deploy logs, Vercel deploy logs, Render deploy logs
- LangSmith / LangFuse trace viewers
- Real-time dashboards (stock tickers, status pages)
