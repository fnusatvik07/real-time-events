"""SSE client - opens one connection and reads events as they arrive.

This is what `EventSource` in a browser does, but spelled out so you can
see the wire format. Watch the timestamps - events arrive ~300ms apart,
NOT all at once at the end.
"""
import time
import httpx

URL = "http://127.0.0.1:8105/stream"

print(f"opening SSE stream: {URL}\n")
t0 = time.time()
with httpx.stream("GET", URL, timeout=30) as r:
    print(f"connection opened. status={r.status_code}, content-type={r.headers.get('content-type')}\n")
    print("raw lines from the stream:")
    for line in r.iter_lines():
        ts = f"+{round((time.time()-t0)*1000):4d}ms"
        if line:
            print(f"  [{ts}]  {line}")
        else:
            print(f"  [{ts}]  ---- end of event ----")

print(f"\nstream closed after {round(time.time()-t0,2)}s")
print("\nKey observations:")
print("  - 10 events arrived ONE AT A TIME, each ~300ms after the last")
print("  - Each event is a few lines (id/event/data) then a BLANK LINE")
print("  - This is exactly what OpenAI's stream=True returns under the hood")
