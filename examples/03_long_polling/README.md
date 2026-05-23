# 03 - Long Polling

The smarter cousin of short polling. The server holds the request open until either data is ready or a timeout fires. The client immediately re-connects.

The server still bumps the counter every 5 seconds. We make 3 long-poll requests; each one returns ~5s later because that's when the next bump happens.

## Run

**Terminal 1:**
```bash
cd examples/03_long_polling
uvicorn server:app --port 8103
```

**Terminal 2:**
```bash
cd examples/03_long_polling
python client.py
```

## Expected output

```
long-poll #1: GET /wait?since=0 (holding...)
  ↓ returned after  5012ms -> {'counter': 1, 'timed_out': False}

long-poll #2: GET /wait?since=1 (holding...)
  ↓ returned after  5007ms -> {'counter': 2, 'timed_out': False}

long-poll #3: GET /wait?since=2 (holding...)
  ↓ returned after  5004ms -> {'counter': 3, 'timed_out': False}
```

## What to point out

- **No wasted polls.** 3 requests covered the same 15 seconds that short polling needed 15 requests for.
- **Lower latency** - response comes ~immediately when data is ready.
- **Cost:** server holds connections open → needs async I/O (we used FastAPI's asyncio handler).
- **Gotcha:** the timeout must be lower than your load balancer's timeout, or the LB will cut the connection.
