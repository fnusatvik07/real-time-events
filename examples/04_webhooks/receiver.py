"""Webhook receiver - the "your backend" side for a Stripe payment scenario.

A small backend for a food-delivery app. Raj just paid 450 INR for biryani
on order order_raj_001. Stripe POSTs the payment event to us. We:

  1. Verify the HMAC signature (otherwise anyone could fake "paid" events)
  2. Dedup by event id (Stripe will sometimes deliver the same event twice)
  3. Queue the work and return 200 fast (Stripe's timeout is 5-10 seconds)

In production "queue the work" means push to Redis / SQS / Kafka. Here it
just prints what the worker would do.

Run:
    uvicorn receiver:app --port 8104
"""
from __future__ import annotations

import hmac
import hashlib
import json
import os
import time
from fastapi import FastAPI, Request, HTTPException

SECRET = os.environ.get("WEBHOOK_SECRET", "whsec_demo_workshop_secret")

app = FastAPI(title="Food delivery payment webhook receiver")

# in-memory dedup. In production this is Redis with a TTL or a DB unique
# index, so duplicate detection survives restarts.
seen_event_ids: set[str] = set()

# in-memory "orders DB"
orders: dict[str, dict] = {
    "order_raj_001": {
        "id": "order_raj_001",
        "customer": "Raj",
        "items": ["Chicken Biryani", "Raita"],
        "amount_inr": 450,
        "status": "awaiting_payment",
    },
}


def verify_signature(body: bytes, signature: str) -> bool:
    """Stripe-style HMAC verification - constant-time compare."""
    expected = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def process_event(event: dict) -> dict:
    """The 'business logic' the worker would run. Prints what we'd do."""
    etype = event["type"]
    order_id = event["data"]["object"]["metadata"]["order_id"]
    order = orders.get(order_id)
    actions = []

    if etype == "payment_intent.succeeded":
        if order:
            order["status"] = "paid"
            actions = [
                f"marked order {order_id} as paid in DB",
                f"notified restaurant tablet (order is now visible to kitchen)",
                f"sent SMS to {order['customer']}: 'Payment confirmed for {', '.join(order['items'])}'",
                f"triggered fulfillment agent",
            ]
        else:
            actions = [f"order {order_id} not found in our DB - logged for review"]

    elif etype == "charge.refunded":
        if order:
            order["status"] = "refunded"
            actions = [
                f"marked order {order_id} as refunded",
                f"notified restaurant to cancel preparation",
                f"sent SMS to {order['customer']}: 'Refund of INR {order['amount_inr']} processed'",
            ]

    elif etype == "payment_intent.payment_failed":
        actions = [
            f"logged failed payment for order {order_id}",
            f"sent SMS: 'Payment failed. Tap to retry.'",
        ]

    else:
        actions = [f"event type '{etype}' is not handled by this service"]

    return {"event_type": etype, "order_id": order_id, "actions": actions}


@app.get("/")
def root():
    return {
        "service": "food delivery payment webhook receiver",
        "endpoints": {
            "POST /webhooks/stripe": "receive a Stripe-style signed event",
            "GET  /orders":          "list current orders in our DB",
        },
        "events_seen": len(seen_event_ids),
        "orders": list(orders.values()),
    }


@app.get("/orders")
def list_orders():
    return {"orders": list(orders.values())}


@app.post("/webhooks/stripe")
async def stripe_webhook(req: Request):
    body = await req.body()
    signature = req.headers.get("stripe-signature", "")

    # Rule 1 of 4: verify the signature on every request.
    if not verify_signature(body, signature):
        print(f"[webhook]  ✗  REJECTED  bad signature  (someone is trying to spoof events)", flush=True)
        raise HTTPException(status_code=401, detail="invalid signature")

    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="invalid json")

    event_id = event.get("id")
    if not event_id:
        raise HTTPException(status_code=400, detail="missing event id")

    # Rule 2 of 4: idempotent dedup by event id. Stripe will sometimes
    # redeliver. Without this you'd double-process payments.
    if event_id in seen_event_ids:
        print(f"[webhook]  ~  DUPLICATE  event {event_id}  (already processed, returning 200)", flush=True)
        return {"received": True, "duplicate": True}
    seen_event_ids.add(event_id)

    # Rule 3 of 4: respond 2xx within Stripe's 5-10 second timeout.
    # In production we'd ENQUEUE to a worker and return immediately.
    # Here we just print what the worker would do (it's near-instant
    # so the demo stays small).
    result = process_event(event)
    print(f"[webhook]  ✓  ACCEPTED   event {event_id}  type={result['event_type']}", flush=True)
    for action in result["actions"]:
        print(f"[worker ]              would: {action}", flush=True)

    return {"received": True, "duplicate": False, "result": result}
