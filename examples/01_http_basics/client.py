"""HTTP basics - the client walkthrough.

Runs seven small demos against the server with consistent formatting
so the class can SEE exactly what's going over the wire and what each
demo is teaching.

Run AFTER starting the server in another terminal:
    Terminal 1:  uvicorn server:app --port 8101
    Terminal 2:  python client.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Pretty-print helpers (shared across all examples)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _pretty import (
    banner, demo, divider,
    request_line, request_header, request_body,
    show_response,
    lesson, note, warn,
)

import httpx

BASE = "http://127.0.0.1:8101"


# ===========================================================================
banner(
    "HTTP basics - what every web request actually does",
    "seven small demos. read along: REQUEST -> RESPONSE -> LESSON",
)


# ---- Demo 1 ----
demo(1, "a plain GET request - no parameters, no auth")
request_line("GET", f"{BASE}/time")
r = httpx.get(f"{BASE}/time")
show_response(r)
lesson(
    "The server returned data and the conversation ended. The TCP "
    "connection may be re-used for the next request (keep-alive), but "
    "from HTTP's view this transaction is complete."
)

divider()


# ---- Demo 2 ----
demo(2, "path parameter, and the server calls a REAL external API")
request_line("GET", f"{BASE}/weather/Bengaluru")
note("(behind the scenes our server will call https://wttr.in)")
try:
    r = httpx.get(f"{BASE}/weather/Bengaluru", timeout=15)
    show_response(r)
    lesson(
        "Most real backends are not static. They glue together databases "
        "and third-party APIs to assemble each response. From the client's "
        "perspective it's still one request, one response."
    )
except httpx.HTTPError as e:
    warn(f"weather call failed ({e}) - wttr.in may be slow today, continuing.")

divider()


# ---- Demo 3 ----
demo(3, "'stateless' means the server has no memory of YOU")
note("calling /counter three times in a row from this same client:")
print()
for _ in range(3):
    request_line("GET", f"{BASE}/counter")
    r = httpx.get(f"{BASE}/counter")
    show_response(r)
    print()
lesson(
    "The server clearly HAS state - the counter goes up. But that state "
    "is GLOBAL. Any other client hitting this same endpoint would also "
    "bump it. The server has no concept of 'this is the same caller as before'."
)

divider()


# ---- Demo 4 ----
demo(4, "identifying yourself - the Authorization header")

note("--- call A: NO header (the server has no idea who we are) ---")
print()
request_line("GET", f"{BASE}/me")
r = httpx.get(f"{BASE}/me")
show_response(r)
print()
note("--- call B: same endpoint, now WITH an Authorization header ---")
print()
request_line("GET", f"{BASE}/me")
request_header("Authorization", "Bearer alice")
r = httpx.get(f"{BASE}/me", headers={"Authorization": "Bearer alice"})
show_response(r)
lesson(
    "HTTP carries no session between requests. You must re-present your "
    "identity (a token, cookie, etc.) on EVERY request. The server reads "
    "it, decides who you are, then immediately forgets when the response is sent."
)

divider()


# ---- Demo 5 ----
demo(5, "POST - creating data on the server")
body = {"title": "Buy biryani", "user": "alice"}
request_line("POST", f"{BASE}/notes")
request_body(body)
r = httpx.post(f"{BASE}/notes", json=body)
show_response(r)
note_id = r.json()["id"]
lesson(
    "POST creates resources. 201 Created means 'I made the new thing'. The "
    "response body contains the created resource - typically with a "
    "server-generated id and timestamp."
)

divider()


# ---- Demo 6 ----
demo(6, f"GET the note back (note_id = {note_id})")
request_line("GET", f"{BASE}/notes/{note_id}")
r = httpx.get(f"{BASE}/notes/{note_id}")
show_response(r)
lesson(
    "The note persists on the server (in memory for this demo). Notice we "
    "had to ASK for it - the server didn't notify anyone about the "
    "creation. That is the limitation real-time patterns work around."
)

divider()


# ---- Demo 7 ----
demo(7, "requesting something that doesn't exist")
request_line("GET", f"{BASE}/notes/9999")
r = httpx.get(f"{BASE}/notes/9999")
show_response(r)
lesson(
    "404 Not Found is the universal 'I checked, that resource isn't here'. "
    "Combined with 401 (auth required) and 403 (forbidden), these are the "
    "errors you'll see most often when consuming APIs."
)

divider()


# ---- Recap ----
banner("Recap")
print()
print("  Every request was independent. None depended on a prior request")
print("  being remembered by the server.")
print()
print("  The server has DATA (notes, counter) but no memory of CLIENTS.")
print("  'Stateless' refers to client identity, not to data persistence.")
print()
print("  Identifying yourself means re-sending auth on EVERY request.")
print()
print("  The server can NEVER push to us. We must always initiate.")
print()
print("  That last point is the limitation every real-time pattern works")
print("  around. Read examples/02_short_polling next.")
print()
