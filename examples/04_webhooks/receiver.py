"""Webhook receiver - verifies HMAC, dedups by event id.

This is the kind of endpoint Stripe/GitHub/Slack POSTs to.

Run: uvicorn receiver:app --port 8104
"""
import hmac
import hashlib
import json
import os
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()
SECRET = os.environ.get("WEBHOOK_SECRET", "shh-this-is-secret")
seen_ids: set[str] = set()


def verify(body: bytes, sig: str) -> bool:
    expected = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig or "")


@app.get("/")
def root():
    return {"ok": True, "seen": len(seen_ids)}


@app.post("/webhook")
async def webhook(req: Request):
    body = await req.body()
    sig = req.headers.get("x-signature", "")

    # 1. Verify the signature - without this, attackers can spoof events
    if not verify(body, sig):
        print("  [receiver] REJECTED bad signature")
        raise HTTPException(401, "invalid signature")

    # 2. Parse and basic validation
    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(400, "invalid json")

    if "id" not in event:
        raise HTTPException(400, "missing event id")

    # 3. Idempotency / dedup - same event id is a no-op
    if event["id"] in seen_ids:
        print(f"  [receiver] DUPLICATE {event['id']} - returning 200 with duplicate flag")
        return {"ok": True, "duplicate": True}

    # 4. Process (in real life: enqueue work, return 200 fast)
    seen_ids.add(event["id"])
    print(f"  [receiver] ACCEPTED {event['id']} type={event.get('type')}")
    return {"ok": True, "duplicate": False}
