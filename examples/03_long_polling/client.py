"""Long polling client - make 3 long-poll requests in a row.

Each request HOLDS open until the server has a new value.
Compare the latencies: each one returns the moment data is ready.
"""
import time
import httpx

BASE = "http://127.0.0.1:8103"
last_seen = 0

for i in range(3):
    t0 = time.time()
    print(f"\nlong-poll #{i+1}: GET /wait?since={last_seen} (holding...)")
    r = httpx.get(f"{BASE}/wait?since={last_seen}&timeout=10", timeout=15)
    elapsed = round((time.time() - t0) * 1000)
    data = r.json()
    last_seen = data["counter"]
    print(f"  ↓ returned after {elapsed:5d}ms -> {data}")

print()
print("Each long-poll returned IMMEDIATELY when new data was ready -")
print("no fixed-interval staleness, and the server held one open request")
print("instead of being hit every second.")
