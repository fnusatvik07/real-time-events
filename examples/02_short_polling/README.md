# 02 - Short Polling (Swiggy-style order tracker)

Realistic scenario: Raj places an order on a food-delivery app and the app shows live status (placed -> confirmed -> cooking -> ... -> delivered) by polling the server.

The order takes ~40 seconds end-to-end. With a 1.5-second poll interval that's ~25 polls. Only 6 of them (the status transitions) carry new information. The other ~19 are pure waste. This example makes that visible.

## What the server does

`POST /orders` creates an order and kicks off a background task that walks it through realistic stages with realistic delays:

| Stage                  | Delay before this stage |
|------------------------|-------------------------|
| placed                 | 0 s (initial)           |
| restaurant_confirmed   | 5 s                     |
| preparing              | 8 s                     |
| rider_assigned         | 5 s                     |
| picked_up              | 7 s                     |
| out_for_delivery       | 6 s                     |
| delivered              | 10 s                    |

`GET /orders/{id}` returns the current state.

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

## What you'll see

The client prints a poll-by-poll table:

```
  poll #   elapsed  status                     verdict
  -------  -------  -------------------------  ----------
        1     0.0s  placed                     NEW
        2     1.5s  placed                     (same)
        3     3.0s  placed                     (same)
        4     4.5s  placed                     (same)
        5     6.0s  restaurant_confirmed       NEW
        6     7.6s  restaurant_confirmed       (same)
        ...
```

Then a summary:

```
  Total time to delivery               41.2 s
  Total polls fired                    28
  Polls that saw a NEW status          7  (25%)
  Polls that were REDUNDANT            21  (75%)
```

## Talking points for the class

- **The 75% waste ratio is at THIS interval.** Tighten to 0.5s and waste hits 90+%. Loosen to 5s and latency hurts.
- **Multiply by 10K simultaneous orders** and Maya is paying for millions of useless requests per hour.
- **No amount of polling will beat near-zero latency.** That's what long polling / SSE / WebSockets buy you.
- The pattern is still **right** for slow checks - e.g., "is my batch report ready?" polled every minute. It's wrong here at 1.5s.

## What to try in front of the class

- Edit `POLL_INTERVAL_SEC` to 0.5 - waste shoots up.
- Edit it to 5.0 - waste drops, but you see status changes 2-4 seconds late.
- Run TWO client tabs against the same order id (`python client.py --order-id <id>` - extend if you want) to show that two clients = two times the polling cost.
