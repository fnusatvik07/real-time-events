# 05 - Server-Sent Events (SSE)

The server keeps an HTTP connection open and pushes events down it as they happen.

This is what powers ChatGPT's token-by-token "typing" UI.

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

## Expected output (abridged)

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
  [+3010ms]  event: done
  [+3010ms]  data: stream complete
```

## Try it from curl

```bash
curl -N http://127.0.0.1:8105/stream
```

The `-N` disables buffering so you see each event as it arrives.

## What to point out

- Each event is `id:` / `event:` / `data:` lines followed by a **blank line** (the event separator).
- The client started receiving data within milliseconds and got the rest progressively.
- In a browser this is just:
  ```javascript
  const es = new EventSource('/stream');
  es.addEventListener('token', e => console.log(e.data));
  ```
- The browser handles auto-reconnect and `Last-Event-ID` for resume - for free.
