"""Project 3 - LiveOrder: a single mini-app composing ALL 4 real-time patterns.

The point of this project (vs Projects 1 and 2): instead of showing the SAME
thing implemented different ways, this one is a realistic food-delivery mini-app
where each pattern is used for the job it's actually suited to.

  WEBHOOK (HMAC-signed)   Stripe-style payment event from outside
                          -> /webhooks/payment
                          -> /api/simulate/payment/{order_id}  (fires one at us)

  SSE (status push)       Live order status from server to customer's screen
                          (awaiting_payment -> paid -> cooking -> ... -> delivered)
                          -> /api/orders/{id}/stream

  WEBSOCKET (bidi chat)   Customer <-> driver chat tied to an order
                          -> /api/chat/{order_id}?role=customer|driver

  SSE (LLM token stream)  AI restaurant recommender, real OpenAI under the hood
                          -> /api/recommend

  POLLING (batch job)     Long-running revenue report; UI polls until done
                          -> POST /api/reports/revenue
                          -> GET  /api/reports/{job_id}

All five run in this one FastAPI app on port 7000. The frontend at /
shows them all on a single page with each card labeled by its pattern.

Run:
    uvicorn server:app --reload --port 7000
Open:
    http://localhost:7000/
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import random
import time
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

ROOT = Path(__file__).parent
STATIC = ROOT / "static"

# Shared webhook secret. In production, per-customer signing keys; demo only here.
WEBHOOK_SECRET = os.environ.get("LIVEORDER_WEBHOOK_SECRET", "liveorder-demo-whsec-7c2a")

# Self-URL used by the simulator endpoint to POST to our own webhook handler.
SELF_BASE = "http://127.0.0.1:7000"

llm = AsyncOpenAI()  # uses OPENAI_API_KEY


# ===========================================================================
# Order model + state machine
# ===========================================================================
STAGES = [
    "awaiting_payment",       # initial
    "paid",                   # webhook arrives
    "restaurant_confirmed",   # 3s after paid
    "cooking",                # 5s after confirmed
    "out_for_delivery",       # 5s after cooking starts
    "delivered",              # 8s after out for delivery
]
TRANSITION_DELAY_SEC = {
    "paid": 3,
    "restaurant_confirmed": 5,
    "cooking": 5,
    "out_for_delivery": 8,
}
STAGE_LABEL = {
    "awaiting_payment":      "Waiting for payment",
    "paid":                  "Payment received - waiting for restaurant",
    "restaurant_confirmed":  "Restaurant accepted the order",
    "cooking":               "Restaurant is cooking",
    "out_for_delivery":      "Out for delivery",
    "delivered":             "Delivered. Enjoy!",
}


@dataclass
class Order:
    id: str
    customer: str
    item: str
    amount_inr: int
    status: str = "awaiting_payment"
    created_at: float = field(default_factory=time.time)
    last_updated_at: float = field(default_factory=time.time)
    timeline: list[dict] = field(default_factory=list)


orders: dict[str, Order] = {}

# Per-order SSE subscribers. Each subscriber is an asyncio.Queue that
# receives every event for that order (status change, webhook, etc.).
order_subscribers: dict[str, list[asyncio.Queue]] = {}


def order_id() -> str:
    return "ord_" + uuid.uuid4().hex[:10]


async def fan_out(order_id_: str, event: dict):
    """Push an event to every SSE subscriber on this order."""
    for q in order_subscribers.get(order_id_, []):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass


async def transition_to(order: Order, new_status: str, note: str = ""):
    """Mutate the order, append a timeline entry, fan-out to SSE subscribers."""
    order.status = new_status
    order.last_updated_at = time.time()
    entry = {
        "at": order.last_updated_at,
        "status": new_status,
        "label": STAGE_LABEL.get(new_status, new_status),
        "note": note,
    }
    order.timeline.append(entry)
    await fan_out(order.id, {
        "kind": "status",
        "status": new_status,
        "label": entry["label"],
        "note": note,
        "at": entry["at"],
    })


async def auto_advance(order: Order):
    """After payment, walk the order forward through cooking -> delivered."""
    try:
        await asyncio.sleep(TRANSITION_DELAY_SEC["paid"])
        await transition_to(order, "restaurant_confirmed", "Restaurant says yes")
        await asyncio.sleep(TRANSITION_DELAY_SEC["restaurant_confirmed"])
        await transition_to(order, "cooking", "On the stove")
        await asyncio.sleep(TRANSITION_DELAY_SEC["cooking"])
        await transition_to(order, "out_for_delivery", "Driver picked it up")
        await asyncio.sleep(TRANSITION_DELAY_SEC["out_for_delivery"])
        await transition_to(order, "delivered", "Bon appetit")
    except asyncio.CancelledError:
        pass


# ===========================================================================
# Chat rooms (WebSocket)
# ===========================================================================
chat_rooms: dict[str, list[tuple[str, WebSocket]]] = {}


async def chat_broadcast(order_id_: str, msg: dict, exclude: WebSocket | None = None):
    payload = json.dumps(msg)
    dead = []
    for role, ws in chat_rooms.get(order_id_, []):
        if ws is exclude:
            continue
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append((role, ws))
    for entry in dead:
        try:
            chat_rooms[order_id_].remove(entry)
        except ValueError:
            pass
    # Also publish chat msgs onto the order's SSE stream so the UI can show them
    # in the order timeline if it wants to.
    if msg.get("type") == "msg":
        await fan_out(order_id_, {"kind": "chat", **msg})


# ===========================================================================
# Webhook crypto
# ===========================================================================
def sign(body: bytes) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


def verify(body: bytes, signature: str) -> bool:
    if not signature:
        return False
    return hmac.compare_digest(sign(body), signature)


# ===========================================================================
# Reports (polling)
# ===========================================================================
@dataclass
class Report:
    id: str
    kind: str
    status: str = "pending"        # pending -> running -> done | error
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    result: dict | None = None


reports: dict[str, Report] = {}


async def run_revenue_report(report: Report):
    report.status = "running"
    # Simulate a long aggregation. In real life: a multi-table SQL query,
    # a Spark/BigQuery job, a cron-style ETL, etc.
    await asyncio.sleep(8)
    paid = [o for o in orders.values() if o.status in
            ("paid", "restaurant_confirmed", "cooking", "out_for_delivery", "delivered")]
    total_inr = sum(o.amount_inr for o in paid)
    by_status = {s: sum(1 for o in paid if o.status == s) for s in STAGES}
    report.result = {
        "orders_counted": len(paid),
        "total_revenue_inr": total_inr,
        "average_ticket_inr": (total_inr / len(paid)) if paid else 0,
        "by_status": by_status,
        "generated_at": time.time(),
    }
    report.status = "done"
    report.finished_at = time.time()


# ===========================================================================
# App + lifecycle
# ===========================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.environ.get("OPENAI_API_KEY"):
        print("[warn] OPENAI_API_KEY not set; /api/recommend will return error events")
    yield


app = FastAPI(title="LiveOrder - all 4 real-time patterns in one app", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/about")
def about():
    return {
        "service": "LiveOrder demo",
        "patterns": {
            "webhook":   ["POST /webhooks/payment", "POST /api/simulate/payment/{order_id}"],
            "sse":       ["GET /api/orders/{id}/stream", "POST /api/recommend"],
            "websocket": ["WS /api/chat/{order_id}?role=customer|driver"],
            "polling":   ["POST /api/reports/revenue", "GET /api/reports/{id}"],
            "rest":      ["POST /api/orders", "GET /api/orders/{id}"],
        },
    }


# ===========================================================================
# Orders (REST + SSE)
# ===========================================================================
@app.post("/api/orders", status_code=201)
async def create_order(req: Request):
    body = await req.json()
    order = Order(
        id=order_id(),
        customer=body.get("customer", "Raj"),
        item=body.get("item", "Chicken Biryani"),
        amount_inr=int(body.get("amount_inr", 450)),
    )
    order.timeline.append({
        "at": order.created_at,
        "status": "awaiting_payment",
        "label": STAGE_LABEL["awaiting_payment"],
        "note": "Order placed",
    })
    orders[order.id] = order
    return order_dict(order)


@app.get("/api/orders/{order_id_}")
def get_order(order_id_: str):
    o = orders.get(order_id_)
    if not o:
        raise HTTPException(404, "order not found")
    return order_dict(o)


@app.get("/api/orders/{order_id_}/stream")
async def stream_order(order_id_: str):
    """SSE stream of everything happening to this order: status changes,
    webhooks received, chat messages. UI subscribes and re-renders on each event.
    """
    order = orders.get(order_id_)
    if not order:
        raise HTTPException(404, "order not found")

    q: asyncio.Queue = asyncio.Queue(maxsize=100)
    order_subscribers.setdefault(order_id_, []).append(q)

    async def gen():
        # First, emit the current snapshot so a late subscriber sees state immediately.
        yield f"event: snapshot\ndata: {json.dumps(order_dict(order))}\n\n"
        try:
            while True:
                try:
                    evt = await asyncio.wait_for(q.get(), timeout=20.0)
                    yield f"event: {evt['kind']}\ndata: {json.dumps(evt)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            try:
                order_subscribers[order_id_].remove(q)
            except ValueError:
                pass

    return StreamingResponse(gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
    })


def order_dict(o: Order) -> dict:
    return {
        "id": o.id,
        "customer": o.customer,
        "item": o.item,
        "amount_inr": o.amount_inr,
        "status": o.status,
        "status_label": STAGE_LABEL.get(o.status, o.status),
        "created_at": o.created_at,
        "last_updated_at": o.last_updated_at,
        "timeline": o.timeline,
    }


# ===========================================================================
# Webhooks (HMAC-signed)
# ===========================================================================
@app.post("/webhooks/payment")
async def webhook_payment(req: Request):
    body = await req.body()
    signature = req.headers.get("stripe-signature") or req.headers.get("x-signature", "")
    if not verify(body, signature):
        raise HTTPException(401, "invalid signature")

    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(400, "invalid json")

    etype = event.get("type", "")
    target_order_id = event.get("data", {}).get("object", {}).get("metadata", {}).get("order_id")

    # Tell the UI a webhook arrived (independent of whether it matches an order).
    if target_order_id:
        await fan_out(target_order_id, {
            "kind": "webhook",
            "event_id": event.get("id"),
            "type": etype,
            "received_at": time.time(),
        })

    if etype == "payment_intent.succeeded" and target_order_id in orders:
        order = orders[target_order_id]
        if order.status == "awaiting_payment":
            await transition_to(order, "paid", "Payment confirmed via webhook")
            asyncio.create_task(auto_advance(order))
            return {"ok": True, "transitioned": "paid"}
        return {"ok": True, "duplicate_transition": True}

    return {"ok": True, "ignored": "no match"}


@app.post("/api/simulate/payment/{order_id_}")
async def simulate_payment(order_id_: str):
    """Construct a Stripe-shaped payment_intent.succeeded event for this order
    with a valid HMAC signature, then POST it to our own /webhooks/payment.

    Same shape Stripe would actually send. Useful for demo without ngrok.
    """
    order = orders.get(order_id_)
    if not order:
        raise HTTPException(404, "order not found")

    event = {
        "id": f"evt_{uuid.uuid4().hex[:12]}",
        "type": "payment_intent.succeeded",
        "created": int(time.time()),
        "data": {
            "object": {
                "id": f"pi_{uuid.uuid4().hex[:14]}",
                "amount": order.amount_inr * 100,
                "currency": "inr",
                "customer": f"cus_{order.customer.lower()}",
                "metadata": {"order_id": order.id},
            }
        },
    }
    body = json.dumps(event).encode()
    sig = sign(body)

    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{SELF_BASE}/webhooks/payment",
            content=body,
            headers={"content-type": "application/json", "stripe-signature": sig},
            timeout=5,
        )
    return {"sent": True, "received_by_webhook": r.status_code, "event_id": event["id"]}


# ===========================================================================
# Chat (WebSocket)
# ===========================================================================
@app.websocket("/api/chat/{order_id_}")
async def chat(ws: WebSocket, order_id_: str, role: str = "customer"):
    if role not in ("customer", "driver"):
        await ws.close(code=4001, reason="role must be customer or driver")
        return
    if order_id_ not in orders:
        await ws.close(code=4004, reason="order not found")
        return

    await ws.accept()
    chat_rooms.setdefault(order_id_, []).append((role, ws))

    # Announce presence
    await chat_broadcast(order_id_, {
        "type": "presence", "user": role, "online": True,
        "text": f"{role} joined the chat",
    }, exclude=ws)
    await ws.send_text(json.dumps({
        "type": "system",
        "text": f"connected as {role} on order {order_id_}",
    }))

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            mtype = msg.get("type")
            if mtype == "msg":
                await chat_broadcast(order_id_, {
                    "type": "msg",
                    "from": role,
                    "text": msg.get("text", "")[:500],
                    "ts": time.time(),
                })
    except WebSocketDisconnect:
        pass
    finally:
        try:
            chat_rooms[order_id_].remove((role, ws))
        except ValueError:
            pass
        await chat_broadcast(order_id_, {
            "type": "presence", "user": role, "online": False,
            "text": f"{role} left",
        })


# ===========================================================================
# AI restaurant recommender (SSE LLM streaming)
# ===========================================================================
RECOMMEND_SYSTEM = """\
You are the food recommender agent for LiveOrder, an Indian food delivery app.
Be helpful and concise (3 sentences max). Suggest specific dishes when you can,
with rough prices in INR. Don't use markdown headers.
"""


@app.post("/api/recommend")
async def recommend(req: Request):
    body = await req.json()
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(400, "prompt required")

    async def gen():
        yield f"event: open\ndata: {json.dumps({'prompt': prompt})}\n\n"
        try:
            stream = await llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": RECOMMEND_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                stream=True,
            )
            i = 0
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield f"id: {i}\nevent: token\ndata: {json.dumps({'text': delta})}\n\n"
                    i += 1
            yield f"event: done\ndata: {json.dumps({'tokens': i})}\n\n"
        except Exception as exc:
            yield f"event: error\ndata: {json.dumps({'message': str(exc)})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
    })


# ===========================================================================
# Revenue report (polling)
# ===========================================================================
@app.post("/api/reports/revenue", status_code=202)
async def report_revenue():
    """Kick off a long-running revenue report. Returns a job_id immediately;
    UI polls /api/reports/{id} until status == done.
    """
    r = Report(id="rep_" + uuid.uuid4().hex[:10], kind="revenue")
    reports[r.id] = r
    asyncio.create_task(run_revenue_report(r))
    return {"id": r.id, "status": r.status, "poll_url": f"/api/reports/{r.id}"}


@app.get("/api/reports/{report_id_}")
def get_report(report_id_: str):
    r = reports.get(report_id_)
    if not r:
        raise HTTPException(404, "report not found")
    elapsed_ms = round((time.time() - r.started_at) * 1000)
    return {
        "id": r.id,
        "kind": r.kind,
        "status": r.status,
        "elapsed_ms": elapsed_ms,
        "result": r.result,
    }
