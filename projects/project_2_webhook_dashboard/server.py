"""Project 2: Webhook-Driven Live Dashboard

A complete pipeline that demonstrates THREE patterns working together:

  webhook IN  -> backend stores + fans out  ->  SSE dashboard + polling fallback
  (server →     (your backend, this file)      (browser, two implementations
   server)                                       so students see the diff)

External services (Stripe, GitHub, etc.) POST signed events to /webhook/payment.
We verify HMAC, dedup by event id, persist to a local SQLite DB, then push the
event live to every connected dashboard.

The dashboard shows the same event feed two ways:
  - Polling tab: GET /events?since=N every 2s
  - Live tab:    SSE /stream pushes events as they arrive

There's also a simulator endpoint that fires fake webhook events so you don't
need ngrok/Stripe to demo the live behavior in class.

Run:
    uvicorn server:app --reload --port 9000
Open:
    http://localhost:9000/
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import random
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

ROOT = Path(__file__).parent
STATIC = ROOT / "static"
DB_PATH = ROOT / "events.db"

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "workshop-secret-do-not-use-in-prod")


# ---------------------------------------------------------------------------
# DB layer (SQLite - keeps the demo self-contained, swap for Postgres in prod)
# ---------------------------------------------------------------------------
def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS events (
            seq         INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id    TEXT UNIQUE NOT NULL,
            type        TEXT NOT NULL,
            payload     TEXT NOT NULL,
            received_at REAL NOT NULL
        );
        """)


def insert_event(event_id: str, etype: str, payload: dict[str, Any]) -> int | None:
    """Returns the new seq, or None if this event_id was already seen."""
    try:
        cur = db().execute(
            "INSERT INTO events(event_id, type, payload, received_at) VALUES (?, ?, ?, ?)",
            (event_id, etype, json.dumps(payload), time.time()),
        )
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None


def fetch_events_since(seq: int, limit: int = 100) -> list[dict]:
    rows = db().execute(
        "SELECT seq, event_id, type, payload, received_at FROM events WHERE seq > ? ORDER BY seq ASC LIMIT ?",
        (seq, limit),
    ).fetchall()
    out = []
    for r in rows:
        out.append({
            "seq": r["seq"],
            "event_id": r["event_id"],
            "type": r["type"],
            "payload": json.loads(r["payload"]),
            "received_at": r["received_at"],
        })
    return out


# ---------------------------------------------------------------------------
# In-process pub/sub for SSE subscribers
# (in a multi-process deployment you'd replace this with Redis pub-sub)
# ---------------------------------------------------------------------------
class Hub:
    def __init__(self):
        self.subscribers: set[asyncio.Queue] = set()

    async def publish(self, event: dict):
        for q in list(self.subscribers):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                # drop slow consumers rather than block the producer
                self.subscribers.discard(q)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self.subscribers.discard(q)


hub = Hub()


# ---------------------------------------------------------------------------
# HMAC signature verification (Stripe-style)
# ---------------------------------------------------------------------------
def make_signature(body: bytes, secret: str = WEBHOOK_SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def verify_signature(body: bytes, signature: str, secret: str = WEBHOOK_SECRET) -> bool:
    if not signature:
        return False
    expected = make_signature(body, secret)
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# App + lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Webhook → Live Dashboard", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


# ---------------------------------------------------------------------------
# WEBHOOK INTAKE - this is what an external service like Stripe POSTs to
# ---------------------------------------------------------------------------
@app.post("/webhook/payment")
async def webhook_payment(req: Request):
    body = await req.body()
    sig = req.headers.get("x-signature", "")

    if not verify_signature(body, sig):
        # Don't leak why exactly - just refuse
        raise HTTPException(401, "invalid signature")

    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(400, "invalid json")

    event_id = event.get("id")
    etype = event.get("type")
    if not event_id or not etype:
        raise HTTPException(400, "missing id or type")

    seq = insert_event(event_id, etype, event)
    if seq is None:
        # Idempotent dedup - already saw this event id
        return {"ok": True, "duplicate": True}

    # Publish to live SSE subscribers - don't block the HTTP response on this
    await hub.publish({
        "seq": seq,
        "event_id": event_id,
        "type": etype,
        "payload": event,
        "received_at": time.time(),
    })

    return {"ok": True, "seq": seq}


# ---------------------------------------------------------------------------
# POLLING ENDPOINT - the "old way" the dashboard can use as a fallback
# ---------------------------------------------------------------------------
@app.get("/events")
def get_events(since: int = 0, limit: int = 100):
    return JSONResponse({"events": fetch_events_since(since, limit)})


# ---------------------------------------------------------------------------
# LIVE SSE STREAM - the modern way the dashboard pushes to UI
# ---------------------------------------------------------------------------
@app.get("/stream")
async def stream_events(since: int = 0):
    """SSE stream.

    1) Replay any events newer than `since` from the DB (catch-up)
    2) Then push new events live as they arrive via the in-process Hub
    """
    async def gen():
        # 1) Catch up from DB
        for e in fetch_events_since(since):
            yield f"id: {e['seq']}\nevent: payment\ndata: {json.dumps(e)}\n\n"

        # 2) Subscribe to live feed
        q = hub.subscribe()
        try:
            yield "event: ready\ndata: subscribed\n\n"
            while True:
                try:
                    evt = await asyncio.wait_for(q.get(), timeout=15.0)
                    yield f"id: {evt['seq']}\nevent: payment\ndata: {json.dumps(evt)}\n\n"
                except asyncio.TimeoutError:
                    # keep-alive ping so proxies don't kill the connection
                    yield ": keep-alive\n\n"
        finally:
            hub.unsubscribe(q)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# SIMULATOR - fires fake (but properly signed) webhook events at ourselves
# so the demo works without ngrok/Stripe in the workshop.
# ---------------------------------------------------------------------------
EVENT_TYPES = ["payment.succeeded", "payment.failed", "refund.created", "subscription.renewed"]
CUSTOMERS = ["Alice", "Bob", "Charlie", "Dana", "Eve", "Frank"]


def fake_event() -> dict:
    return {
        "id": f"evt_{uuid.uuid4().hex[:12]}",
        "type": random.choice(EVENT_TYPES),
        "created": int(time.time()),
        "data": {
            "customer": random.choice(CUSTOMERS),
            "amount_cents": random.randint(500, 50000),
            "currency": "USD",
        },
    }


@app.post("/simulate/burst")
async def simulate_burst(n: int = 5):
    """Fire N fake webhook events at our own /webhook/payment with valid signature."""
    import httpx
    results = []
    async with httpx.AsyncClient() as client:
        for _ in range(n):
            body_obj = fake_event()
            body = json.dumps(body_obj).encode()
            sig = make_signature(body)
            r = await client.post(
                "http://127.0.0.1:9000/webhook/payment",
                content=body,
                headers={"x-signature": sig, "content-type": "application/json"},
                timeout=5,
            )
            results.append({"status": r.status_code, "body": r.json()})
            await asyncio.sleep(0.15)
    return {"fired": len(results), "results": results}


@app.post("/simulate/replay")
async def simulate_replay():
    """Send the SAME event twice - proves the dedup logic works."""
    import httpx
    body_obj = fake_event()
    body = json.dumps(body_obj).encode()
    sig = make_signature(body)
    async with httpx.AsyncClient() as client:
        a = await client.post("http://127.0.0.1:9000/webhook/payment",
                              content=body,
                              headers={"x-signature": sig, "content-type": "application/json"})
        b = await client.post("http://127.0.0.1:9000/webhook/payment",
                              content=body,
                              headers={"x-signature": sig, "content-type": "application/json"})
    return {"first": a.json(), "second": b.json()}


@app.post("/simulate/forgery")
async def simulate_forgery():
    """Try POSTing WITHOUT a valid signature - should be rejected."""
    import httpx
    body_obj = fake_event()
    body = json.dumps(body_obj).encode()
    async with httpx.AsyncClient() as client:
        r = await client.post("http://127.0.0.1:9000/webhook/payment",
                              content=body,
                              headers={"x-signature": "deadbeef", "content-type": "application/json"})
    return {"status": r.status_code, "body_text": r.text}


@app.post("/admin/reset")
def admin_reset():
    """Wipe the DB - handy between demos."""
    DB_PATH.unlink(missing_ok=True)
    init_db()
    return {"ok": True}
