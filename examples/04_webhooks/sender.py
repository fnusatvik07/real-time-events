"""Webhook sender - simulates Stripe firing events at our food-delivery backend.

Sends four scenarios in sequence:
  1. payment_intent.succeeded  for order_raj_001 (Raj's 450 INR biryani)
       -> server marks the order paid, notifies the restaurant, sends an SMS
  2. payment_intent.succeeded  for the SAME event id again
       -> server returns 200 but with duplicate:true (no double-charge)
  3. charge.refunded           for order_raj_001
       -> server marks it refunded and tells the restaurant to cancel
  4. payment_intent.succeeded  with a BAD signature
       -> server returns 401 (this is what stops attackers from faking events)

Run AFTER starting the receiver:
    Terminal 1:  uvicorn receiver:app --port 8104
    Terminal 2:  python sender.py
"""
from __future__ import annotations

import hmac
import hashlib
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _pretty import (
    banner, demo, divider,
    request_line, request_header, request_body, show_response,
    lesson, note, ok, fail, preflight_check,
)

import httpx

URL = "http://127.0.0.1:8104/webhooks/stripe"
SECRET = "whsec_demo_workshop_secret"

preflight_check("http://127.0.0.1:8104", expected_keyword="food delivery payment webhook")


def sign(body: bytes) -> str:
    return hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def send(event: dict, *, signature: str | None) -> httpx.Response:
    body = json.dumps(event).encode()
    headers = {"content-type": "application/json"}
    if signature is not None:
        headers["stripe-signature"] = signature
    return httpx.post(URL, content=body, headers=headers, timeout=5)


def show_full_request(event: dict, signature: str | None):
    request_line("POST", URL)
    if signature:
        request_header("stripe-signature", signature[:16] + "...")
    request_header("content-type", "application/json")
    request_body(event)


def make_payment_event(event_id: str, order_id: str, amount_inr: int, customer: str):
    return {
        "id": event_id,
        "type": "payment_intent.succeeded",
        "created": int(time.time()),
        "data": {
            "object": {
                "id": f"pi_{event_id[-8:]}",
                "amount": amount_inr * 100,
                "currency": "inr",
                "customer": f"cus_{customer.lower()}",
                "metadata": {"order_id": order_id},
            }
        },
    }


def make_refund_event(event_id: str, order_id: str):
    return {
        "id": event_id,
        "type": "charge.refunded",
        "created": int(time.time()),
        "data": {
            "object": {
                "id": f"ch_{event_id[-8:]}",
                "amount_refunded": 45000,
                "metadata": {"order_id": order_id},
            }
        },
    }


banner(
    "Webhooks - Stripe payment events for a food delivery app",
    "4 scenarios: valid payment, duplicate delivery, refund, forged event",
)


# ---- Case 1: properly signed payment ----------------------------------
demo(1, "Case 1: properly signed payment_intent.succeeded")
event = make_payment_event("evt_pay_raj_001", "order_raj_001", 450, "Raj")
body = json.dumps(event).encode()
show_full_request(event, sign(body))
r = send(event, signature=sign(body))
show_response(r)
lesson(
    "Server verified the HMAC, deduplicated by event id (first time seen), "
    "queued the work (which we printed inline for visibility), and returned "
    "200. In production that 'queue' is Redis or SQS, and the worker "
    "process pulls events independently."
)

divider()


# ---- Case 2: same event delivered again -------------------------------
demo(2, "Case 2: same event id arrives a second time (Stripe retried)")
note("Stripe will sometimes deliver the same event twice - retries, race conditions, etc.")
note("Our handler must be safe to call repeatedly. Watch for duplicate:true.")
print()
show_full_request(event, sign(body))
r = send(event, signature=sign(body))
show_response(r)
lesson(
    "Same event id -> dedup hit. Returned 200 (Stripe is happy) with "
    "duplicate:true so any downstream consumer knows not to act on it "
    "again. Without this, you'd double-mark the order paid, double-notify "
    "the restaurant, and double-send the SMS."
)

divider()


# ---- Case 3: refund event ---------------------------------------------
demo(3, "Case 3: a refund event for the same order")
refund = make_refund_event("evt_refund_raj_001", "order_raj_001")
refund_body = json.dumps(refund).encode()
show_full_request(refund, sign(refund_body))
r = send(refund, signature=sign(refund_body))
show_response(r)
lesson(
    "A webhook receiver typically handles MANY event types. The handler is "
    "a small switch on event.type. New event types should default to "
    "logging and returning 200 - never 5xx, or Stripe will retry forever."
)

divider()


# ---- Case 4: forgery attempt ------------------------------------------
demo(4, "Case 4: an attacker tries to fake a payment event")
note("Without signature verification, anyone with the webhook URL could POST")
note("this and trick us into shipping free food. Watch our defense.")
print()
fake = make_payment_event("evt_fake_attacker_001", "order_raj_001", 10000, "attacker")
show_full_request(fake, signature="deadbeef_this_is_obviously_fake")
r = send(fake, signature="deadbeef_this_is_obviously_fake")
show_response(r)
lesson(
    "Constant-time HMAC compare with the timestamped body is the single "
    "most important webhook security measure. Always present, never "
    "skipped. Use hmac.compare_digest (not ==) to prevent timing attacks."
)

divider()


# ---- Recap ------------------------------------------------------------
banner("The four webhook rules in one place")
print()
print("  1. Return 2xx FAST           don't do real work in the handler")
print("                               (queue it, let a worker process it)")
print()
print("  2. Verify the signature      on EVERY request, constant-time compare")
print()
print("  3. Dedup by event id         senders will sometimes deliver twice")
print()
print("  4. Don't 5xx on bad data     return 200 + log; 5xx triggers retries")
print()
print("  Follow these and your webhook receiver will be boring and reliable.")
print("  Skip any one and you'll have very interesting outages.")
print()
