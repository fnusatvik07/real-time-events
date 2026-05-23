# 2. Polling

> **TL;DR:** Polling is the simplest real-time-ish pattern - the client repeatedly asks the server "anything new?" Short polling is dumb and wasteful but reliable; long polling is smarter but more complex to implement on the server side.

---

## 2.1 What is polling?

The client wants to know about server-side changes. Vanilla HTTP can't push, so the client takes matters into its own hands: it asks. Repeatedly.

```
CLIENT                   SERVER
  |  GET /messages ----->  |
  |  <---- 200 [] -------  |   (nothing yet)
  |                        |
  |  (wait 2 seconds)      |
  |                        |
  |  GET /messages ----->  |
  |  <---- 200 [] -------  |   (still nothing)
  |                        |
  |  (wait 2 seconds)      |
  |                        |
  |  GET /messages ----->  |
  |  <---- 200 [msg1] ---  |   (finally!)
```

---

## 2.2 Short polling

**Short polling** is the version above: the server immediately responds with whatever it has (or nothing), and the client keeps re-asking on a fixed interval.

### The minimal example

**Client (JavaScript):**
```javascript
setInterval(async () => {
  const res = await fetch('/api/messages?since=' + lastSeenId);
  const messages = await res.json();
  if (messages.length) {
    render(messages);
    lastSeenId = messages[messages.length - 1].id;
  }
}, 2000);  // poll every 2 seconds
```

**Server (Python / FastAPI):**
```python
@app.get("/api/messages")
def get_messages(since: int = 0):
    return [m for m in store.messages if m.id > since]
```

### What's good about short polling

- **Dead simple.** Anyone who can make an HTTP request can poll.
- **Works through any network** that allows HTTP - no special protocols, no special infrastructure, plays nice with proxies/firewalls.
- **Stateless on the server.** Easy to scale horizontally.
- **No special connection management.** Connections come and go; no need to track who's listening.

### What's bad about short polling

- **Wasteful.** If nothing changes for 10 minutes, you make ~300 useless requests (at 2-second interval). Each costs: bandwidth, CPU, log-line, possibly DB query, possibly auth check.
- **Latency.** Average latency is **half the poll interval**. Poll every 2s → average 1s of staleness, worst-case 2s.
- **You can't win on both fronts.** Lower the interval and latency improves but cost explodes. Raise it and cost drops but UX feels stale.
- **Thundering herd.** If many clients poll on the same schedule (e.g., aligned to wall-clock minute), you can get traffic spikes.

### When short polling is genuinely fine

- The data updates rarely and a few seconds of staleness is OK (status of a long batch job)
- You're hitting a backend that only supports REST (most third-party APIs)
- Number of clients is small
- You're in a constrained environment (no WebSocket support, etc.)
- You're a small team and the engineering cost of anything fancier is not worth it

### Smart things to do with short polling

- **Conditional requests:** use `ETag` / `If-None-Match` or `Last-Modified` / `If-Modified-Since`. The server returns `304 Not Modified` with an empty body when nothing changed. Cuts bandwidth massively.
- **Cursor / "since" parameter:** always include `?since=<last_id>` so responses are deltas, not full lists.
- **Exponential backoff:** if many polls in a row return empty, increase the interval. Reset when something arrives.
- **Jitter:** add random offset to the interval so clients don't sync up.

---

## 2.3 Long polling

**Long polling** is short polling's smarter cousin. The client sends a request, but the server **does not respond immediately**. Instead, the server holds the request open until either:
- new data is available, OR
- a timeout fires (typically 30s)

When the response comes back, the client immediately fires another request and the cycle repeats.

```
CLIENT                   SERVER
  |  GET /messages ----->  |
  |                        |  (server holds the request, waiting)
  |                        |
  |                        |  ... 8 seconds later, a message arrives ...
  |                        |
  |  <---- 200 [msg1] ---  |
  |  GET /messages ----->  |  (immediately reconnects)
  |                        |  (holding again)
  |                        |
  |                        |  ... 30s pass, no message ...
  |  <---- 200 [] -------  |  (timeout, send empty response)
  |  GET /messages ----->  |  (reconnects)
```

### Why long polling is better

- **Lower latency:** clients get the message essentially as soon as the server has it (no fixed-interval wait).
- **Fewer requests:** instead of 300 polls in 10 idle minutes, you might do 20 (one every 30s timeout).
- **Same HTTP semantics:** still vanilla HTTP, works through proxies, etc.

### Why long polling is harder

- **Server must hold connections.** That means async I/O - you can't have one thread per held request, or you'll run out of threads at the first hundred users. Use `asyncio`, Node, Go, Tokio, etc.
- **Proxy/load-balancer timeouts.** Many LBs cut connections at 60s. Your timeout must be lower than that.
- **Server-side "wake-up" mechanism.** When a message arrives, you need to signal **the held request** for the right user. Usually a per-user `asyncio.Event`, a Redis pub-sub, or in-process queue.
- **Reconnect loop.** Client must reconnect immediately on every response - easy to get wrong (forgetting to reconnect on error = client goes silent forever).

### Long polling - code sketch (FastAPI)

```python
import asyncio
from fastapi import FastAPI

app = FastAPI()
events: dict[str, asyncio.Queue] = {}

def queue_for(user: str) -> asyncio.Queue:
    return events.setdefault(user, asyncio.Queue())

@app.get("/poll/{user}")
async def long_poll(user: str):
    q = queue_for(user)
    try:
        # wait up to 30s for an event
        msg = await asyncio.wait_for(q.get(), timeout=30.0)
        return {"event": msg}
    except asyncio.TimeoutError:
        return {"event": None}   # tell client to reconnect

@app.post("/push/{user}")
async def push(user: str, payload: dict):
    await queue_for(user).put(payload)
    return {"ok": True}
```

---

## 2.4 Short vs long polling - when to use which

| Question | Use short polling | Use long polling |
|----------|-------------------|------------------|
| Updates rare, staleness OK? | ✅ | overkill |
| Need sub-second latency? | ❌ (use SSE/WS) | maybe |
| Many concurrent clients, mostly idle? | ❌ (wasteful) | ✅ |
| Server stack supports async? | doesn't matter | required |
| Behind aggressive proxies? | ✅ | might cut connections |

---

## 2.5 Where polling fits in modern AI apps

- **Polling a long-running task.** Agent kicks off a 5-minute research job. Frontend polls `/jobs/{id}` every 3 seconds for status. (Or, better, use SSE - but polling is the simple fallback.)
- **Checking external API status.** OpenAI Batch API, fine-tuning jobs, Anthropic Files API - all polled because they don't push back.
- **Heartbeat / liveness for agent dashboards.** Light polling for "is the agent process still running?"
- **Cron-like agent triggers.** Agent polls a calendar or events table every minute looking for new work.

---

## 2.6 Anti-patterns

- ❌ **Polling every 100ms.** Switch to SSE or WS - your backend will thank you.
- ❌ **Returning full lists on every poll.** Use a cursor (`since`, `after`, `etag`).
- ❌ **No backoff.** If the server is down or returning errors, you'll DDoS your own backend with retries.
- ❌ **Polling without authentication caching.** Each poll re-validating a JWT signature is fine; each poll hitting a DB to re-load user permissions is not.
- ❌ **Long polling with synchronous I/O.** You will run out of threads almost immediately.

---

## Mental model

**Polling = client keeps asking.**
Short polling: ask on a timer. Long polling: ask, wait, ask again.

It's the lowest-tech option and frequently the right one. Don't be embarrassed to polling.
