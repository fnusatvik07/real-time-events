# Live-Class Teaching Guide

> What to demo, when to demo it, what to type, and what the audience will see. Designed for a 60-90 minute live session covering polling, webhooks, SSE, and WebSockets.

---

## What's in the repo (the cast)

You have **two layers of runnable material**:

1. **Examples** (`examples/01_..` through `examples/07_..`) - seven tiny self-contained folders, one per topic. Each is **30-150 lines of code** with a `server.py` and `client.py` (or `receiver.py` and `sender.py` for webhooks). The point is "show me the pattern in the smallest possible code."

2. **Projects** (`projects/project_1_..` and `projects/project_2_..`) - two full apps with HTML UIs that **combine multiple patterns** so the class can SEE the difference in the browser, not just in logs.

**Recommended teaching arc:**

- Start with concepts + diagrams (10 min per topic).
- Show the **example** for that topic in a terminal (5 min). Audience sees the wire format.
- After all four topics are covered, show **Project 1** to compare polling vs SSE vs WS in one browser window (10 min).
- Close with **Project 2** to show webhooks + SSE working together in a realistic pipeline (10 min).

---

## Pre-class setup (do this once, before the class)

```bash
cd /Users/datasense/Desktop/realtime
source .venv/bin/activate

# Smoke test - make sure everything boots
cd examples && bash qa.sh
```

This takes ~2 minutes and asserts all 7 examples + both projects work end-to-end. If this passes, you're ready.

**Open these tabs in advance** so you can switch quickly:

- Terminal split into 2 panes (server on left, client on right)
- Browser tab: http://localhost:8000 (Project 1)
- Browser tab: http://localhost:9000 (Project 2)
- Browser tab: GitHub repo with the diagrams folder open
- Browser tab: the concept docs folder

---

## EXAMPLE 1 - HTTP basics (`examples/01_http_basics`)

**Purpose:** establish the baseline. Remind everyone what plain HTTP looks like before we talk about real-time.

**Files:**
- `server.py` (15 lines) - FastAPI app with `/` and `/echo` endpoints
- `client.py` (16 lines) - makes 3 requests with httpx

**Live demo:**

Terminal 1:
```bash
cd examples/01_http_basics
uvicorn server:app --port 8101
```

Terminal 2:
```bash
cd examples/01_http_basics
python client.py
```

**What the audience sees:**
- Client prints status code, body, and a hit_number that increments
- Each request is independent - server treats them as strangers walking up to a counter

**Key talking points:**
- "Server cannot speak unless asked"
- "Each request is independent"
- "This is the limitation everything we'll see today works around"

**Bonus:** `curl -v http://localhost:8101/` to show the actual HTTP request and response on the wire.

---

## EXAMPLE 2 - Short polling (`examples/02_short_polling`)

**Purpose:** see polling waste with your own eyes.

**Files:**
- `server.py` - FastAPI app that bumps a counter every 5 seconds in the background
- `client.py` - polls every 1 second for 15 seconds, prints which polls saw a new value

**Live demo:**

Terminal 1:
```bash
cd examples/02_short_polling
uvicorn server:app --port 8102
```

Terminal 2:
```bash
cd examples/02_short_polling
python client.py
```

**What the audience sees:**

```
polling http://127.0.0.1:8102/value every 1.0s for 15s
  t= 0.0s  poll # 1  -> 0  (NEW)
  t= 1.0s  poll # 2  -> 0
  t= 2.1s  poll # 3  -> 0
  t= 3.1s  poll # 4  -> 0
  t= 4.1s  poll # 5  -> 0
  t= 5.1s  poll # 6  -> 1  (NEW)
  t= 6.1s  poll # 7  -> 1
  ...
summary: 15 polls, 3 actually saw a new value, 12 were redundant
waste ratio: 80%
```

**Key talking points:**
- 80% waste at this rate
- "Lower the interval → more waste, raise it → more lag"
- Multiply by 10K users and 24 hours and the cost is real money
- This is fine for some cases (we'll see when in the decision matrix)

---

## EXAMPLE 3 - Long polling (`examples/03_long_polling`)

**Purpose:** show the same pattern, smarter. Server holds the request until data arrives.

**Files:**
- `server.py` - same bumper, but adds `/wait?since=N&timeout=10` that holds until counter > N
- `client.py` - makes 3 long-poll requests in sequence, prints latency

**Live demo:**

Terminal 1:
```bash
cd examples/03_long_polling
uvicorn server:app --port 8103
```

Terminal 2:
```bash
cd examples/03_long_polling
python client.py
```

**What the audience sees:**

```
long-poll #1: GET /wait?since=0 (holding...)
  ↓ returned after  5012ms -> {'counter': 1, 'timed_out': False}
long-poll #2: GET /wait?since=1 (holding...)
  ↓ returned after  5007ms -> {'counter': 2, 'timed_out': False}
long-poll #3: GET /wait?since=2 (holding...)
  ↓ returned after  5004ms -> {'counter': 3, 'timed_out': False}
```

**Key talking points:**
- 3 requests covered 15 seconds (short polling needed 15)
- Each response is near-instant when data arrives
- Server uses `async`/`await` to hold connections without burning threads
- Watch out for proxy timeouts in production - set server timeout BELOW LB timeout

---

## EXAMPLE 4 - Webhooks (`examples/04_webhooks`)

**Purpose:** flip the direction. Show signature verification, dedup, and signature rejection in one script.

**Files:**
- `receiver.py` (35 lines) - the "your backend" side. HMAC verification, dedup by event id.
- `sender.py` (40 lines) - the "Stripe" side. Sends 3 test cases.

**Live demo:**

Terminal 1:
```bash
cd examples/04_webhooks
uvicorn receiver:app --port 8104
```

Terminal 2:
```bash
cd examples/04_webhooks
python sender.py
```

**What the audience sees (sender side):**

```
=== Case 1: properly signed event ===
  -> HTTP 200  {'ok': True, 'duplicate': False}

=== Case 2: SAME event again (test dedup) ===
  -> HTTP 200  {'ok': True, 'duplicate': True}

=== Case 3: unsigned event (attacker) ===
  -> HTTP 401  body: {"detail":"invalid signature"}
```

**Receiver side simultaneously:**
```
  [receiver] ACCEPTED evt_workshop_001 type=payment.succeeded
  [receiver] DUPLICATE evt_workshop_001 — returning 200 with duplicate flag
  [receiver] REJECTED bad signature
```

**Key talking points:**
- Three rules: verify signature, dedup by ID, return 2xx fast
- Show the `verify()` function - just 3 lines
- Mention `hmac.compare_digest` vs `==` (timing attack defense)
- Real-world: this is exactly the shape of a Stripe / GitHub webhook receiver

**Bonus demo:** show how to write the same with curl + openssl from the README, to prove there's no magic.

---

## EXAMPLE 5 - SSE (`examples/05_sse`)

**Purpose:** see the wire format. Demystify "streaming."

**Files:**
- `server.py` (20 lines) - streams 10 events spaced 300ms apart
- `client.py` (20 lines) - consumes the stream with httpx, prints each raw line as it arrives

**Live demo:**

Terminal 1:
```bash
cd examples/05_sse
uvicorn server:app --port 8105
```

Terminal 2:
```bash
cd examples/05_sse
python client.py
```

**What the audience sees:**

```
opening SSE stream: http://127.0.0.1:8105/stream
connection opened. status=200, content-type=text/event-stream

raw lines from the stream:
  [+   2ms]  id: 0
  [+   2ms]  event: token
  [+   2ms]  data: token-0
  [+   2ms]  ---- end of event ----
  [+ 304ms]  id: 1
  [+ 304ms]  event: token
  [+ 304ms]  data: token-1
  [+ 304ms]  ---- end of event ----
  ...
```

**Key talking points:**
- "Look at the timestamps - this is streaming, not buffering"
- Show the wire format: `id:`, `event:`, `data:`, blank line
- "This is exactly what OpenAI's `stream=True` returns. The SDK is just an SSE parser with JSON on top."
- "Browser: `new EventSource('/stream')` + `addEventListener('token', ...)`. Two lines. Done."

**Bonus:** `curl -N http://localhost:8105/stream` to confirm the same in pure curl with no Python.

---

## EXAMPLE 6 - WebSockets (`examples/06_websockets`)

**Purpose:** show full duplex. Show broadcast.

**Files:**
- `server.py` (25 lines) - echo + broadcast server using FastAPI WebSocket
- `client.py` (30 lines) - connects, sends 3 messages, prints replies

**Live demo:**

Terminal 1:
```bash
cd examples/06_websockets
uvicorn server:app --port 8106
```

Terminal 2:
```bash
cd examples/06_websockets
python client.py
```

**Terminal 3 (powerful demo - run a second client in parallel):**
```bash
cd examples/06_websockets
python client.py
```

**What the audience sees:**
- Both clients receive each other's messages
- Server log shows `[server] client 1234 said: 'hello'` etc.
- The connection stays open between messages (one TCP socket the whole time)

**Key talking points:**
- "We dialed once. Then we sent and received freely. That's the difference vs SSE."
- "Try running 3 copies in parallel - broadcast scales naturally."
- Mention scaling: 50K connections is achievable on one process; past that needs Redis pub/sub.

**Browser console bonus:**
```javascript
const ws = new WebSocket('ws://127.0.0.1:8106/ws');
ws.onmessage = e => console.log('RECV:', e.data);
ws.onopen = () => ws.send('hi from browser');
```

---

## EXAMPLE 7 - Real-world OpenAI streaming (`examples/07_openai_streaming`)

**Purpose:** the "aha" moment. Everything in Example 5 was a toy - now show the REAL thing.

**Files:**
- `client.py` (35 lines) - uses `openai` SDK with `stream=True` to count to 10
- No server (talks to api.openai.com)

**Live demo:**

```bash
cd examples/07_openai_streaming
python client.py
```

**What the audience sees:**

```
Asking the LLM to count from one to ten.

Streamed response (each chunk is one SSE event):

One
Two
Three
...
Ten

first token: 350ms
total      : 980ms
chunks     : 11
```

**Key talking points:**
- "What you just saw IS Example 5. OpenAI's server is sending SSE events. The SDK is parsing them for you."
- "This is the same pattern behind ChatGPT, Claude.ai, Cursor, Copilot - all of them."

**Killer bonus:** show the raw SSE with curl:
```bash
OPENAI_API_KEY=$(grep ^OPENAI_API_KEY ../../.env | cut -d= -f2-)
curl -N https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "content-type: application/json" \
  -d '{"model":"gpt-4o-mini","stream":true,"messages":[{"role":"user","content":"count to 5"}]}'
```

You'll see `data: {"choices":[{"delta":{"content":"One"}}]}` line by line. Audience reactions: "ohhhh."

---

## PROJECT 1 - Streaming AI Chat (`projects/project_1_streaming_chat`)

**Purpose:** make the UX cost of each pattern VISCERAL. Same LLM call, three patterns, side by side in one browser window.

**What it has:**
- FastAPI backend with `/api/polling/...`, `/api/sse/chat`, `/api/ws/chat` endpoints
- HTML page with three "cards" - one per pattern
- Each card shows: input, send button, metrics (status, first byte, total time, token count), output area

**Live demo:**

Terminal:
```bash
cd projects/project_1_streaming_chat
uvicorn server:app --reload --port 8000
```

Browser: http://localhost:8000

**Demo script:**

1. **Type the same prompt in all three input boxes.** Something like "Write a 100-word story about a robot."
2. **Click "Run" on the polling card first.**
   - Audience sees a spinner. Nothing happens for 3-5 seconds. Then the WHOLE response appears at once.
   - Metrics show: ~5000ms first byte, ~5000ms total.
3. **Click "Stream" on the SSE card.**
   - Audience sees words pouring in immediately.
   - First byte: ~500ms. Total: ~3000ms.
4. **Click "Stream" on the WebSocket card.**
   - Same streaming experience as SSE.
   - **Then click "Interrupt" while it's mid-response.** The streaming stops. Server confirms `interrupted`. THIS IS THE WEBSOCKET DIFFERENCE.
5. **Open DevTools → Network tab and re-run each.** Show:
   - Polling: many separate HTTP requests
   - SSE: one request with `EventStream` tab open showing individual events
   - WebSocket: one connection with `Messages` tab showing frames

**Key talking points:**
- "Same backend code. Same OpenAI call. Three patterns. The UX difference is dramatic."
- "WebSocket gives you interrupt for free. SSE can't."
- "But if you don't need interrupt, SSE is simpler and cheaper."

---

## PROJECT 2 - Webhook-Driven Dashboard (`projects/project_2_webhook_dashboard`)

**Purpose:** show the full pipeline. Webhook arrives → backend stores → SSE pushes to dashboards. Two dashboards (polling vs SSE) compare the receiving side.

**What it has:**
- FastAPI backend with `/webhook/payment`, `/events?since=N` (polling), `/stream` (SSE)
- Built-in simulators: `/simulate/burst?n=5`, `/simulate/replay`, `/simulate/forgery`
- HTML page with two dashboards side-by-side and control buttons

**Live demo:**

Terminal:
```bash
cd projects/project_2_webhook_dashboard
uvicorn server:app --reload --port 9000
```

Browser: http://localhost:9000

**Demo script:**

1. **Open DevTools → Network → filter by "/events" or "/stream".**
2. **Watch the idle period.** Polling dashboard fires `/events?since=N` every 2 seconds. SSE dashboard has ONE long open connection.
3. **Click "+1 event".**
   - SSE dashboard updates instantly.
   - Polling dashboard updates on the next 2-second tick.
4. **Click "+5 events"** to show a burst.
5. **Click "Send duplicate (test dedup)".**
   - Server returns `{first: {ok:true, seq:N}, second: {ok:true, duplicate:true}}`.
   - Dashboard only shows it once.
6. **Click "Send unsigned (test security)".**
   - Server returns HTTP 401.
   - Nothing appears in either dashboard.
7. **Click "Disconnect" on SSE, fire 3 events, click "Reconnect".**
   - The reconnected SSE client gets the 3 missed events (catch-up replay).

**Key talking points:**
- "Look at the network tab - polling has been firing the whole time, SSE has been silent."
- "Multiply by 10K users idle for 8 hours, and the cost gap is massive."
- "The webhook handler is THIN: verify, dedup, return 200. Real work happens in workers."
- "The browser auto-reconnects SSE for you - you don't write reconnection code."

---

## Timing template for a 90-minute class

| Time | Block | Material |
|------|-------|----------|
| 0:00-0:05 | Intro - the four patterns and why they exist | Overview doc + diagram 12 (decision tree) |
| 0:05-0:15 | HTTP foundation | Concept doc 01 + diagram 01 + Example 1 |
| 0:15-0:30 | Polling | Concept doc 02 + diagrams 02-04 + Examples 2 & 3 |
| 0:30-0:45 | Webhooks | Concept doc 03 + diagrams 05-07 + Example 4 |
| 0:45-1:00 | SSE | Concept doc 04 + diagrams 08-09 + Examples 5 & 7 |
| 1:00-1:15 | WebSockets | Concept doc 05 + diagrams 10-11 + Example 6 |
| 1:15-1:25 | Decision matrix + AI/MCP | Concept docs 06-07 + diagrams 12-14 |
| 1:25-1:40 | Project 1 demo (side-by-side chat) | Browser |
| 1:40-1:50 | Project 2 demo (webhook + dashboard) | Browser |
| 1:50-2:00 | Q&A - map participants' own use cases | - |

For a tighter 60-minute version, skip Examples 1 and 3, compress Webhooks to 10 minutes, drop Project 2 (or keep it as the closing demo).

---

## What I'd write on the whiteboard

If I had only one slide, this:

```
              Polling     Webhooks     SSE         WebSocket
              ───────     ────────     ───         ─────────
Who asks?     client      external     client      client (then both)
Direction?    C→S         S→S          S→C         both
Latency?      ~interval/2 instant      instant     instant
Idle cost?    every poll  ZERO         one conn    one conn
Best for?     slow polls  ext events   LLM stream  chat/voice/games
Default?      no          yes for      YES         only if needed
                          ext events
```

Then "any feature you're designing → ask: who initiates? what direction? how often?"

That's the whole workshop in one table.

---

## Common questions you'll get

**"What about gRPC streaming / MQTT / Kafka?"**
Variations on the same patterns. gRPC streaming is essentially SSE/WebSocket-equivalents but binary and typed. MQTT is publish-subscribe over a long-lived TCP connection (kin to WebSocket). Kafka is durable pub-sub backend (the thing you put BEHIND your WebSocket layer when scaling). Same mental model.

**"Can I use SSE for two-way?"**
Use SSE for the server → client direction and a regular `fetch('POST /...')` for client → server. Many apps actually do this. It's not as elegant as WebSocket but is simpler and works through more proxies.

**"What if I don't want to install a webhook receiver - can I just poll?"**
Yes. Webhooks are server-to-server only and require a public URL. If you're a small team without infra, polling is often the right starting point.

**"How do I authenticate WebSockets / SSE in a browser when I can't set headers?"**
Three options: (1) cookie auth (works seamlessly), (2) a short-lived token in the URL (`?ticket=abc`), (3) a polyfill that adds header support. Cookies are the cleanest if you control the domain.

**"What's the difference between SSE and HTTP/2 push?"**
Different things. SSE is application-level events with a defined wire format and an `EventSource` browser API. HTTP/2 push was a server-initiated push of resources (like prefetching CSS); it was deprecated. They're unrelated.

---

## Repo recap

```
realtime/
├── concepts/   8 deep-dive markdown docs - the textbook
├── diagrams/   14 .drawio files + 14 PNG renders + a visual README
├── examples/   7 self-contained folders + qa.sh - the labs
├── projects/   2 full apps - the capstone demos
├── TEACHING.md ← you are here (this file)
└── README.md   - top-level orientation
```

Good luck with the class!
