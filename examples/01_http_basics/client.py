"""HTTP basics - the client walkthrough.

Runs seven small demos against the server, with deliberately verbose
formatting so the class can SEE exactly what's going over the wire
and what each demo is teaching.

Run AFTER starting the server in another terminal:
    Terminal 1:  uvicorn server:app --port 8101
    Terminal 2:  python client.py
"""
from __future__ import annotations

import json
import textwrap

import httpx

BASE = "http://127.0.0.1:8101"
WIDTH = 76


# ---------------------------------------------------------------------------
# Pretty-print helpers - so the audience can read along
# ---------------------------------------------------------------------------
def heading(title: str) -> None:
    print()
    print("=" * WIDTH)
    print(f"  {title}")
    print("=" * WIDTH)


def demo(title: str) -> None:
    print()
    print(f"==>  {title}")
    print()


def hr() -> None:
    print("-" * WIDTH)


def show_request(
    method: str,
    url: str,
    headers: dict | None = None,
    body: dict | None = None,
) -> None:
    print(f"  REQUEST   {method:6s} {url}")
    if headers:
        for k, v in headers.items():
            print(f"            > {k}: {v}")
    if body is not None:
        print(f"            > Body:")
        for line in json.dumps(body, indent=2).splitlines():
            print(f"              {line}")


def show_response(r: httpx.Response) -> None:
    status_word = r.reason_phrase or ""
    ctype = r.headers.get("content-type", "?").split(";")[0]
    print(f"  RESPONSE  {r.status_code} {status_word}   ({ctype})")
    try:
        body = r.json()
        for line in json.dumps(body, indent=2).splitlines():
            print(f"            {line}")
    except Exception:
        text = r.text[:300]
        for line in text.splitlines():
            print(f"            {line}")


def lesson(text: str) -> None:
    print()
    wrapped = textwrap.wrap(text, width=WIDTH - 14)
    for i, line in enumerate(wrapped):
        prefix = "  LESSON    " if i == 0 else "            "
        print(f"{prefix}{line}")


def err(msg: str) -> None:
    print(f"  WARN      {msg}")


# ---------------------------------------------------------------------------
# Demos
# ---------------------------------------------------------------------------
heading("HTTP basics - what every web request actually does")


# ===========================================================================
# Demo 1 - plain GET
# ===========================================================================
demo("Demo 1: a plain GET request - no parameters, no auth")
show_request("GET", f"{BASE}/time")
r = httpx.get(f"{BASE}/time")
show_response(r)
lesson(
    "The server returned data and the conversation ended. The TCP "
    "connection may be re-used for the next request (keep-alive), but "
    "from HTTP's view this transaction is complete."
)

hr()


# ===========================================================================
# Demo 2 - path parameter + real external API
# ===========================================================================
demo("Demo 2: path parameter, and the server calls a REAL external API")
show_request("GET", f"{BASE}/weather/Bengaluru")
print("            (behind the scenes our server will call https://wttr.in)")
try:
    r = httpx.get(f"{BASE}/weather/Bengaluru", timeout=15)
    show_response(r)
    lesson(
        "Most real backends are not static. They glue together databases "
        "and third-party APIs to assemble each response. From the "
        "client's perspective it's still one request, one response."
    )
except httpx.HTTPError as e:
    err(f"weather call failed ({e}). Continuing - wttr.in may be slow.")

hr()


# ===========================================================================
# Demo 3 - the stateless point: shared counter
# ===========================================================================
demo("Demo 3: 'stateless' means the server has no memory of YOU")
print("            calling /counter three times in a row from this client:")
print()
for n in (1, 2, 3):
    show_request("GET", f"{BASE}/counter")
    r = httpx.get(f"{BASE}/counter")
    show_response(r)
    print()
lesson(
    "The server clearly HAS state - the counter goes up. But it's GLOBAL. "
    "Any other client hitting this same endpoint would also bump it. "
    "The server has no concept of 'this is the same caller as before'."
)

hr()


# ===========================================================================
# Demo 4 - identifying yourself via Authorization header
# ===========================================================================
demo("Demo 4: identifying yourself - the Authorization header")

print("  --- call A: NO header (the server has no idea who we are) ---")
print()
show_request("GET", f"{BASE}/me")
r = httpx.get(f"{BASE}/me")
show_response(r)
print()

print("  --- call B: same endpoint, now WITH an Authorization header ---")
print()
headers = {"Authorization": "Bearer alice"}
show_request("GET", f"{BASE}/me", headers=headers)
r = httpx.get(f"{BASE}/me", headers=headers)
show_response(r)
lesson(
    "HTTP carries no session between requests. You must re-present your "
    "identity (a token, cookie, etc.) on EVERY request. The server reads "
    "it, decides who you are, then immediately forgets when the response "
    "is sent."
)

hr()


# ===========================================================================
# Demo 5 - POST creates a resource
# ===========================================================================
demo("Demo 5: POST - creating data on the server")
body = {"title": "Buy biryani", "user": "alice"}
show_request("POST", f"{BASE}/notes", body=body)
r = httpx.post(f"{BASE}/notes", json=body)
show_response(r)
note_id = r.json()["id"]
lesson(
    "POST creates resources. 201 Created means 'I made the new thing'. "
    "The response body contains the created resource - typically with "
    "a server-generated id and timestamp."
)

hr()


# ===========================================================================
# Demo 6 - GET the resource we just created
# ===========================================================================
demo(f"Demo 6: GET the note back (note_id = {note_id})")
show_request("GET", f"{BASE}/notes/{note_id}")
r = httpx.get(f"{BASE}/notes/{note_id}")
show_response(r)
lesson(
    "The note persists on the server (in memory for this demo). Notice "
    "we had to ASK for it - the server didn't notify anyone about the "
    "creation. That is the limitation real-time patterns work around."
)

hr()


# ===========================================================================
# Demo 7 - non-existent resource (404)
# ===========================================================================
demo("Demo 7: requesting something that doesn't exist")
show_request("GET", f"{BASE}/notes/9999")
r = httpx.get(f"{BASE}/notes/9999")
show_response(r)
lesson(
    "404 Not Found is the universal 'I checked, that resource isn't here'. "
    "Combined with 401 (auth required) and 403 (forbidden), these are the "
    "errors you'll see most often when consuming APIs."
)

hr()


# ===========================================================================
# Summary
# ===========================================================================
heading("Recap - what every demo had in common")
print()
print("  - Every request was independent. None depended on a prior request")
print("    being remembered by the server.")
print()
print("  - The server has DATA (notes, counter) but no memory of CLIENTS.")
print("    'Stateless' refers to client identity, not to data persistence.")
print()
print("  - Identifying yourself means re-sending auth on EVERY request.")
print()
print("  - The server can NEVER push to us. We must always initiate.")
print()
print("  That last point is the limitation every real-time pattern in this")
print("  workshop works around. Read examples/02_short_polling next.")
print()
