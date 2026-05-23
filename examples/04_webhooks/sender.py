"""Webhook sender - mimics what Stripe/GitHub do when an event fires.

Sends three test cases:
  1. A properly signed event             -> server accepts
  2. The same event again (duplicate)    -> server dedups (returns duplicate:true)
  3. An unsigned event (forgery attempt) -> server rejects with 401
"""
import hmac
import hashlib
import json
import httpx

SECRET = "shh-this-is-secret"
URL = "http://127.0.0.1:8104/webhook"


def sign(body: bytes) -> str:
    return hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()


def send(body_obj: dict, signature: str | None):
    body = json.dumps(body_obj).encode()
    headers = {"content-type": "application/json"}
    if signature is not None:
        headers["x-signature"] = signature
    return httpx.post(URL, content=body, headers=headers)


event = {"id": "evt_workshop_001", "type": "payment.succeeded", "amount_cents": 5000}

print("=== Case 1: properly signed event ===")
body = json.dumps(event).encode()
r = send(event, sign(body))
print(f"  -> HTTP {r.status_code}  {r.json()}")
print()

print("=== Case 2: SAME event again (test dedup) ===")
r = send(event, sign(body))
print(f"  -> HTTP {r.status_code}  {r.json()}")
print()

print("=== Case 3: unsigned event (attacker) ===")
r = send(event, "deadbeef")
print(f"  -> HTTP {r.status_code}  body: {r.text}")
print()

print("Three rules of webhook receivers:")
print("  1. Verify the signature (case 3 -> rejected)")
print("  2. Dedup by event id    (case 2 -> handled gracefully)")
print("  3. Return 200 fast      (queue actual work to the background)")
