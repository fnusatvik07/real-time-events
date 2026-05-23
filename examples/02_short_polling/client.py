"""Short polling client - poll every 1 second for 15 seconds.

Watch how many polls return the same value (waste!) and how
many actually saw a new value (the server bumps every 5s).
"""
import time
import httpx

BASE = "http://127.0.0.1:8102"
INTERVAL = 1.0
DURATION = 15

last_seen = None
polls = 0
new_values = 0
empty_polls = 0
t0 = time.time()

print(f"polling {BASE}/value every {INTERVAL}s for {DURATION}s\n")
while time.time() - t0 < DURATION:
    polls += 1
    r = httpx.get(f"{BASE}/value", timeout=2)
    value = r.json()["counter"]
    elapsed = round(time.time() - t0, 1)
    if value != last_seen:
        new_values += 1
        print(f"  t={elapsed:4.1f}s  poll #{polls:2d}  -> {value}  (NEW)")
        last_seen = value
    else:
        empty_polls += 1
        print(f"  t={elapsed:4.1f}s  poll #{polls:2d}  -> {value}")
    time.sleep(INTERVAL)

print()
print(f"summary: {polls} polls, {new_values} actually saw a new value, {empty_polls} were redundant")
print(f"waste ratio: {empty_polls / polls * 100:.0f}%")
print()
print("Lower the interval -> more wasted requests.")
print("Raise the interval -> higher latency.")
print("This is the fundamental short-polling trade-off.")
