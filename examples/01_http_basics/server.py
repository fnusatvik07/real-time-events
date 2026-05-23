"""HTTP basics - a small but realistic FastAPI server.

This server is intentionally a little bigger than "hello world" so the class
can see what a real backend does on every request:

  - GET  /              friendly index, lists all endpoints
  - GET  /time          pure read - returns server's clock
  - GET  /counter       SHARED global counter (proves "the server has DATA
                        but doesn't know which CLIENT hit it")
  - GET  /me            requires an Authorization header. 401 without it.
                        proves "HTTP has no built-in session - you must
                        re-present your identity on every request."
  - GET  /weather/{city} calls a REAL external API (wttr.in) and returns
                        a slimmed-down response. Shows that "a backend" is
                        usually just glue between other backends.
  - GET  /notes         lists in-memory notes (created via POST)
  - POST /notes         creates a note. Returns 201 Created.
  - GET  /notes/{id}    fetches one note or returns 404 Not Found.

Run:
    uvicorn server:app --port 8101
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

app = FastAPI(title="HTTP basics demo server")


# ---------------------------------------------------------------------------
# Server-side state. Important to call out in the class:
#   This data is "remembered" by the server, BUT the server has no idea
#   which CLIENT created it. Anyone can read or extend it. There is no
#   per-user memory built into HTTP. Per-user memory is something we
#   bolt on with cookies / tokens / sessions.
# ---------------------------------------------------------------------------
notes_db: dict[int, dict] = {}
next_note_id: int = 1
shared_counter: int = 0


# ---------------------------------------------------------------------------
# JWT verification (HS256, the most common signing algorithm in the wild).
# A JWT is just 3 base64-url-encoded strings joined by dots:
#   <header>.<payload>.<signature>
# The signature is HMAC-SHA256(secret, "<header>.<payload>").
# We verify it ourselves (instead of pulling in pyjwt) so students can see
# there's no magic - just base64 and HMAC.
# ---------------------------------------------------------------------------
JWT_SECRET = "demo-only-jwt-secret-do-not-use-in-prod-3f8a"


def _b64url_decode(data: str) -> bytes:
    """Base64-url decode (JWT style: '-_' alphabet, no padding)."""
    padding_needed = (-len(data)) % 4
    return base64.urlsafe_b64decode(data + ("=" * padding_needed))


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def verify_jwt(token: str) -> dict | None:
    """Verify the signature and return the decoded claims, or None if invalid."""
    parts = token.split(".")
    if len(parts) != 3:
        return None
    header_b64, payload_b64, signature_b64 = parts

    # 1. Recompute the expected signature over header.payload
    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected = hmac.new(JWT_SECRET.encode(), signing_input, hashlib.sha256).digest()
    expected_b64 = _b64url_encode(expected)

    # 2. Constant-time compare against what the client sent
    if not hmac.compare_digest(expected_b64, signature_b64):
        return None

    # 3. Decode the payload to claims dict
    try:
        return json.loads(_b64url_decode(payload_b64))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class NoteCreate(BaseModel):
    title: str
    user: str | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/")
def root():
    """Friendly index. Hit this first to see what the server can do."""
    return {
        "service": "HTTP basics demo",
        "endpoints": {
            "GET  /":                "this page",
            "GET  /time":            "server's current time (no state)",
            "GET  /counter":         "increments a SHARED counter",
            "GET  /me":              "requires an Authorization header",
            "GET  /weather/{city}":  "calls a real external API (wttr.in)",
            "GET  /notes":           "list all in-memory notes",
            "POST /notes":           "create a note (returns 201)",
            "GET  /notes/{id}":      "fetch one note (200 or 404)",
        },
    }


@app.get("/time")
def get_time():
    """Pure function. No state read or written. Always safe to call."""
    now = datetime.now(timezone.utc)
    return {
        "server_time_iso": now.isoformat(),
        "unix_seconds": int(now.timestamp()),
        "timezone": "UTC",
    }


@app.get("/counter")
def get_counter():
    """Bumps a SHARED counter and returns its new value.

    Teaching point: the server clearly has state (the number keeps going
    up). But that state is global. The server has no idea who you are.
    Anyone else calling this endpoint right now would see the next value.
    """
    global shared_counter
    shared_counter += 1
    return {
        "counter": shared_counter,
        "note": (
            "This counter is SHARED across all clients. The server didn't "
            "remember you - it just bumped its own number."
        ),
    }


@app.get("/me")
def get_me(authorization: Optional[str] = Header(default=None)):
    """Returns the current user based on the Authorization header.

    This endpoint expects a real HS256 JWT (the same shape Auth0, Clerk,
    Supabase Auth, and most SaaS backends issue). We verify the signature
    using a shared secret and return the decoded claims.

    Teaching point: HTTP itself has no session. The server only knows
    who you are because you TOLD it, on THIS request, via a signed token.
    No header -> 401. Tampered token -> 401. The next request must
    re-present the same (or a refreshed) token.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="missing Authorization header. Send: Authorization: Bearer <jwt>",
        )

    token = authorization[len("Bearer "):].strip()
    claims = verify_jwt(token)
    if not claims:
        raise HTTPException(
            status_code=401,
            detail=(
                "JWT verification failed. Either the token is malformed, "
                "the signature does not match (token was tampered or signed "
                "with a different secret), or required fields are missing."
            ),
        )

    return {
        "user_id":     claims.get("sub"),
        "name":        claims.get("name"),
        "email":       claims.get("email"),
        "scopes":      claims.get("scope", []),
        "issued_at":   claims.get("iat"),
        "expires_at":  claims.get("exp"),
        "note": (
            "I extracted these fields from the JWT you sent on THIS request. "
            "I will not remember you on the next one - you must send the "
            "token again. That's what 'stateless' means."
        ),
    }


@app.get("/weather/{city}")
async def get_weather(city: str):
    """Calls a REAL external API (wttr.in) for the given city.

    Teaching point: backends are usually not static. Most of what a real
    API does is talk to OTHER backends (databases, third-party APIs) and
    assemble a response. From the client's perspective, it's just one
    request - the fan-out is hidden.
    """
    url = f"https://wttr.in/{city}?format=j1"
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.get(url, headers={"User-Agent": "http-basics-demo"})
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"upstream wttr.in error: {exc}",
        )

    current = data["current_condition"][0]
    return {
        "city": city.title(),
        "temperature_c": int(current["temp_C"]),
        "feels_like_c": int(current["FeelsLikeC"]),
        "condition": current["weatherDesc"][0]["value"],
        "humidity_percent": int(current["humidity"]),
        "wind_kph": int(current["windspeedKmph"]),
        "source": "wttr.in (external public API)",
    }


@app.get("/notes")
def list_notes():
    """List all notes currently stored in memory."""
    return {"count": len(notes_db), "notes": list(notes_db.values())}


@app.get("/notes/{note_id}")
def get_note(note_id: int):
    """Fetch one note by id. Returns 404 if it doesn't exist."""
    note = notes_db.get(note_id)
    if not note:
        raise HTTPException(status_code=404, detail=f"note {note_id} not found")
    return note


@app.post("/notes", status_code=201)
def create_note(payload: NoteCreate):
    """Create a new note. Returns 201 Created with the created resource."""
    global next_note_id
    note = {
        "id": next_note_id,
        "title": payload.title,
        "user": payload.user or "anonymous",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    notes_db[next_note_id] = note
    next_note_id += 1
    return note
