"""Long polling client - Raj requests an Uber and waits for a driver to accept.

Compare with example 02 (short polling for an order status).
- Short polling would fire one request every 1-2 seconds for the ~6 seconds
  it takes a driver to accept. That's ~3-6 wasteful requests.
- Long polling fires ONE request. The server holds it. The instant a driver
  accepts, the response comes back. Latency near zero.

Run AFTER starting the server in another terminal:
    Terminal 1:  uvicorn server:app --port 8103
    Terminal 2:  python client.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _pretty import (
    banner, demo, divider,
    request_line, request_body, show_response,
    lesson, note, info, ok, summary_table,
    GREEN, YELLOW, CYAN, DIM, BOLD, RESET,
)

import httpx

BASE = "http://127.0.0.1:8103"


banner(
    "Long polling - Uber-style ride dispatch",
    "one request, held open by the server, replied to the moment a driver accepts",
)


# ---- Step 1: create the ride ------------------------------------------
demo(1, "Raj requests a ride")
body = {"rider": "Raj", "pickup": "Indiranagar Metro Station", "dropoff": "Bengaluru Airport"}
request_line("POST", f"{BASE}/rides")
request_body(body)
r = httpx.post(f"{BASE}/rides", json=body, timeout=5)
show_response(r)
ride_id = r.json()["id"]

divider()


# ---- Step 2: long-poll for driver acceptance --------------------------
demo(2, "Open the long-poll connection and wait for a driver")
request_line("GET", f"{BASE}/rides/{ride_id}/wait")
note("the server will NOT respond immediately; it will hold this request")
note("open until a driver accepts, or up to 30 seconds")
print()
print(f"  {CYAN}{BOLD}WAITING{RESET}   connection open, no traffic flowing...")

t0 = time.time()
try:
    r = httpx.get(f"{BASE}/rides/{ride_id}/wait", timeout=35)
except httpx.ReadTimeout:
    print(f"  {YELLOW}{BOLD}TIMEOUT{RESET}   client-side timeout (server didn't respond in time)")
    sys.exit(1)
elapsed = time.time() - t0

print(f"  {GREEN}{BOLD}REPLIED{RESET}   after {elapsed:.2f} seconds")
print()
show_response(r)

driver = r.json().get("driver")

divider()


# ---- Step 3: summarise vs short polling -------------------------------
demo(3, "Cost comparison: long poll vs short poll")
short_poll_count = max(int(elapsed / 1.5), 1) + 1
summary_table([
    ("Time until driver accepted",                 f"{elapsed:.1f} s"),
    ("Requests we sent (long polling)",            "1"),
    ("Requests we'd have sent if short polling every 1.5s",
                                                   f"~{short_poll_count}"),
    ("Useful requests in either case",             "1  (the one that returned the driver)"),
    ("Wasteful requests with short polling",       f"~{short_poll_count - 1}"),
])
if driver:
    summary_table([
        ("Assigned driver",   driver["name"]),
        ("Vehicle",           driver["vehicle"]),
        ("Rating",            f"{driver['rating']} stars"),
        ("ETA to pickup",     f"{driver['eta_min']} min"),
    ])

lesson(
    "ONE held connection beat what would have been 3-8 round-trip requests. "
    "We also got the answer the moment it was available - no fixed-interval "
    "lag. The price: the server must hold connections open without burning "
    "a thread each, which is why we use async I/O. Also watch for proxy "
    "timeouts (set server timeout BELOW your load balancer's idle timeout)."
)

divider()


# ---- Step 4: simulate the timeout case --------------------------------
demo(4, "What if no driver accepts in time? (timeout dance)")
note("simulating with a very short server-side timeout to keep the demo short")
print()
request_line("GET", f"{BASE}/rides/{ride_id}/wait?timeout=2")
note("(this ride is already accepted, so server returns instantly anyway)")
r = httpx.get(f"{BASE}/rides/{ride_id}/wait?timeout=2", timeout=5)
show_response(r)

lesson(
    "When the timeout fires before data arrives, the server replies with a "
    "marker (timed_out: true here) and the client immediately reconnects. "
    "This loop is what makes long polling 'near-realtime' over plain HTTP."
)

print()
print(f"  Next up: SSE (example 05) gives you a single connection over which the")
print(f"  server can push MANY events without the client reconnecting at all.")
print()
