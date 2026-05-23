"""HTTP basics - client side. One request, one response, then the conversation ends.

Run AFTER starting the server in another terminal.
"""
import httpx

BASE = "http://127.0.0.1:8101"

print("Request 1 ----------------------------------")
r = httpx.get(f"{BASE}/")
print("status :", r.status_code)
print("body   :", r.json())
print()

print("Request 2 (server doesn't remember us) -----")
r = httpx.get(f"{BASE}/")
print("body   :", r.json())
print()

print("Request 3 with a query param ---------------")
r = httpx.get(f"{BASE}/echo", params={"msg": "real-time workshop"})
print("body   :", r.json())
print()

print("Key takeaway:")
print("  Server cannot speak unless asked.")
print("  Each request is independent.")
print("  That's the limitation the other 4 patterns work around.")
