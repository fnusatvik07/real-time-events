"""Short polling client - tracks a Swiggy-style order.

Walks through the realistic scenario:
  1. Raj places an order (POST /orders)
  2. Client polls GET /orders/{id} every 1.5 seconds
  3. Most polls return the SAME status the previous poll saw (waste)
  4. Occasionally a poll catches a status transition (the only useful polls)
  5. Polling stops once status == 'delivered'

The output makes the waste visible so the class can SEE the trade-off.

Run AFTER starting the server in another terminal:
    Terminal 1:  uvicorn server:app --port 8102
    Terminal 2:  python client.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _pretty import (
    banner, demo, divider,
    request_line, response_line, request_body, response_body,
    show_response, lesson, note, info, ok, fail,
    summary_table,
    GREEN, YELLOW, RED, CYAN, DIM, BOLD, RESET,
)

import httpx

BASE = "http://127.0.0.1:8102"
POLL_INTERVAL_SEC = 1.5
MAX_POLLS = 40   # safety net


banner(
    "Short polling - Swiggy-style order tracker",
    f"watch how many polls return the SAME status (= waste).  interval = {POLL_INTERVAL_SEC}s",
)


# ---- Step 1: place the order ------------------------------------------
demo(1, "Raj places an order")
body = {"customer": "Raj", "item": "Chicken Biryani", "amount_inr": 450}
request_line("POST", f"{BASE}/orders")
request_body(body)
r = httpx.post(f"{BASE}/orders", json=body, timeout=5)
show_response(r)
order = r.json()
order_id = order["id"]

divider()


# ---- Step 2: poll until delivered -------------------------------------
demo(2, f"Poll GET /orders/{order_id} every {POLL_INTERVAL_SEC}s until delivered")
print(f"  {DIM}each row below is one poll. green = NEW status, dim grey = redundant.{RESET}")
print()
print(f"  {DIM}{'poll #':>7}  {'elapsed':>8}  {'status':<25}  {'verdict':<10}{RESET}")
print(f"  {DIM}{'-'*7}  {'-'*8}  {'-'*25}  {'-'*10}{RESET}")

last_status: str | None = None
new_status_polls = 0
redundant_polls = 0
total_polls = 0
t0 = time.time()

for i in range(1, MAX_POLLS + 1):
    r = httpx.get(f"{BASE}/orders/{order_id}", timeout=5)
    o = r.json()
    status = o["status"]
    total_polls += 1
    elapsed = time.time() - t0

    if status != last_status:
        new_status_polls += 1
        color = GREEN
        verdict = "NEW"
    else:
        redundant_polls += 1
        color = DIM
        verdict = "(same)"

    print(f"  {color}{i:>7}  {elapsed:>7.1f}s  {status:<25}  {verdict:<10}{RESET}")

    if status == "delivered":
        break
    last_status = status
    time.sleep(POLL_INTERVAL_SEC)
else:
    print()
    print(f"  {RED}reached MAX_POLLS without seeing 'delivered'.{RESET}")

divider()


# ---- Step 3: summarise the waste --------------------------------------
demo(3, "Tally the waste")

waste_pct = (redundant_polls / total_polls * 100) if total_polls else 0
useful_pct = 100 - waste_pct

summary_table([
    ("Order id",                          order_id),
    ("Total time to delivery",            f"{elapsed:.1f} s"),
    ("Total polls fired",                 str(total_polls)),
    ("Polls that saw a NEW status",       f"{new_status_polls}  ({useful_pct:.0f}%)"),
    ("Polls that were REDUNDANT",         f"{redundant_polls}  ({waste_pct:.0f}%)"),
    ("Average gap between status changes",
        f"{(elapsed / max(new_status_polls - 1, 1)):.1f} s"),
])

lesson(
    "Most polls fetched a value we already had. With 10,000 concurrent "
    "orders being tracked at this rate, that's millions of redundant "
    "requests per hour. Lower the interval to feel snappier and waste "
    "more. Raise it to save money and feel laggier. Long polling, SSE, "
    "and WebSockets are the smarter answers to this exact trade-off."
)

divider()


# ---- Step 4: show how to lower the waste ------------------------------
demo(4, "How to make polling cheaper WITHOUT changing patterns")
note("1. Increase the interval when nothing's happening (exponential backoff)")
note("2. Use a 'since' / 'etag' so the server returns 304 Not Modified")
note("3. Pause polling when the browser tab is hidden")
note("4. Use a cursor: ask for 'events since X' instead of 'current state'")
print()
print(f"  See concepts/02_polling.md section 2.5 for full code patterns.")
print()
print(f"  But if you need sub-second latency, none of these help.")
print(f"  The next two examples (long polling, SSE) are the real answer.")
print()
