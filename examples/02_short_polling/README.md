# 02 - Short Polling

Client keeps asking. Server immediately replies with whatever it has (or nothing).

The server bumps a counter every 5 seconds in the background. The client polls every 1 second for 15 seconds - so we expect ~3 polls to find a new value and ~12 to find the same value (the "waste").

## Run

**Terminal 1:**
```bash
cd examples/02_short_polling
uvicorn server:app --port 8102
```

**Terminal 2:**
```bash
cd examples/02_short_polling
python client.py
```

## Expected output (abridged)

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

## What to point out

- **80% of requests did nothing useful.** That's the cost of short polling.
- Lowering the interval → more waste, lower latency.
- Raising the interval → less waste, more staleness.
- You can never have both. That's why long polling (next example) exists.
