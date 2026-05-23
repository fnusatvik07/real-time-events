"""HTTP basics - the client walkthrough.

Runs seven small demos against the server with consistent formatting
so the class can SEE exactly what's going over the wire and what each
demo is teaching.

Run AFTER starting the server in another terminal:
    Terminal 1:  uvicorn server:app --port 8101
    Terminal 2:  python client.py
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
import time
from pathlib import Path

# Pretty-print helpers (shared across all examples)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _pretty import (
    banner, demo, divider, pause,
    request_line, request_header, request_body,
    show_response,
    lesson, note, warn, preflight_check,
    CYAN, DIM, BOLD, RESET, MAGENTA, GREEN, YELLOW,
)

import httpx

BASE = "http://127.0.0.1:8101"
preflight_check(BASE, expected_keyword="HTTP basics demo")


# ---------------------------------------------------------------------------
# Minimal JWT helper - same shared secret as the server.
# A JWT is just three base64-url-encoded chunks joined by dots:
#     <header>.<payload>.<signature>
# We build one by hand here so students can see there's no magic.
# In production you'd use a library: pyjwt, jose, or whatever your stack uses.
# ---------------------------------------------------------------------------
JWT_SECRET = "demo-only-jwt-secret-do-not-use-in-prod-3f8a"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def make_jwt(claims: dict) -> str:
    """Build a real HS256 JWT for the given claims."""
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = _b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_b64 = _b64url(json.dumps(claims, separators=(",", ":")).encode())
    signing_input = f"{header_b64}.{payload_b64}".encode()
    signature = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    return f"{header_b64}.{payload_b64}.{_b64url(signature)}"


def decode_jwt_parts(token: str) -> tuple[dict, dict, str]:
    """Decode header + payload (for display); leave the signature opaque."""
    header_b64, payload_b64, sig_b64 = token.split(".")
    pad = lambda s: s + "=" * ((-len(s)) % 4)
    header  = json.loads(base64.urlsafe_b64decode(pad(header_b64)))
    payload = json.loads(base64.urlsafe_b64decode(pad(payload_b64)))
    return header, payload, sig_b64


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
pause()


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
pause()


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
pause()


# ---- Demo 4 ----
demo(4, "identifying yourself - JWT in the Authorization header")

note("This is how nearly every modern SaaS does auth: short-lived signed JSON")
note("Web Tokens (JWTs). The server verifies the signature; if it matches, the")
note("server trusts the claims inside.")

# Build a real JWT for our user. In a real app this is issued by a login
# endpoint after the user enters their email/password (or via OAuth).
now = int(time.time())
claims = {
    "sub":   "usr_arjun_8c3d2",
    "name":  "Arjun Kumar",
    "email": "arjun.kumar@liveorder.app",
    "iat":   now,
    "exp":   now + 3600,
    "scope": ["orders:read", "orders:write"],
}
jwt = make_jwt(claims)

# Show students what's inside the JWT so they don't think it's opaque magic.
print()
print(f"  {CYAN}{BOLD}JWT we built for Arjun:{RESET}")
print(f"  {DIM}{jwt}{RESET}")
print()
print(f"  {CYAN}decoded parts:{RESET}")
header_dict, payload_dict, sig_b64 = decode_jwt_parts(jwt)
print(f"    {YELLOW}header  {RESET}{json.dumps(header_dict)}")
print(f"    {YELLOW}payload {RESET}{json.dumps(payload_dict)}")
print(f"    {YELLOW}signature{RESET} {sig_b64[:24]}... {DIM}(HMAC-SHA256 of header+payload, "
      f"signed with the shared secret){RESET}")

print()
note("--- call A: NO header (server has no idea who we are) ---")
print()
request_line("GET", f"{BASE}/me")
r = httpx.get(f"{BASE}/me")
show_response(r)

print()
note("--- call B: WITH our real JWT (server verifies the signature, returns claims) ---")
print()
request_line("GET", f"{BASE}/me")
request_header("Authorization", f"Bearer {jwt[:40]}...{jwt[-12:]}")
r = httpx.get(f"{BASE}/me", headers={"Authorization": f"Bearer {jwt}"})
show_response(r)

print()
note("--- call C: TAMPERED JWT (we change a claim but keep the old signature) ---")
note("    swap name 'Arjun Kumar' -> 'Hacker Admin' in the payload, leave the signature.")
print()
# Tamper: build a new payload (different name) with the OLD signature
evil_claims = {**claims, "name": "Hacker Admin", "scope": ["admin"]}
evil_payload_b64 = _b64url(json.dumps(evil_claims, separators=(",", ":")).encode())
header_b64, _, real_sig_b64 = jwt.split(".")
tampered_jwt = f"{header_b64}.{evil_payload_b64}.{real_sig_b64}"

request_line("GET", f"{BASE}/me")
request_header("Authorization", f"Bearer {tampered_jwt[:40]}...{tampered_jwt[-12:]}")
r = httpx.get(f"{BASE}/me", headers={"Authorization": f"Bearer {tampered_jwt}"})
show_response(r)

lesson(
    "Three takeaways. (1) HTTP has no built-in session - you re-present your "
    "JWT on every request. (2) A JWT is just base64(header).base64(payload)."
    "HMAC-SHA256 of those. (3) Tampering the payload without the secret "
    "breaks the signature, so the server rejects it - which is exactly why "
    "JWTs work as auth tokens."
)

divider()
pause()


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
pause()


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
pause()


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
pause()


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
