# 04 - Webhooks

Server-to-server event delivery: external service POSTs to your URL, you verify the signature, dedup, return 200 fast.

This example ships two scripts - a `receiver.py` that simulates **your** backend, and a `sender.py` that simulates **Stripe/GitHub** firing an event.

## Run

**Terminal 1** (the receiver - your backend):
```bash
cd examples/04_webhooks
uvicorn receiver:app --port 8104
```

**Terminal 2** (fire three test cases):
```bash
cd examples/04_webhooks
python sender.py
```

## Expected output

**Sender terminal:**
```
=== Case 1: properly signed event ===
  -> HTTP 200  {'ok': True, 'duplicate': False}

=== Case 2: SAME event again (test dedup) ===
  -> HTTP 200  {'ok': True, 'duplicate': True}

=== Case 3: unsigned event (attacker) ===
  -> HTTP 401  body: {"detail":"invalid signature"}
```

**Receiver terminal:**
```
  [receiver] ACCEPTED evt_workshop_001 type=payment.succeeded
  [receiver] DUPLICATE evt_workshop_001 - returning 200 with duplicate flag
  [receiver] REJECTED bad signature
```

## What to point out

1. **Signature verification matters.** Without it, anyone with your URL can post fake `payment.succeeded` events.
2. **Idempotency by event ID.** Senders retry on errors and sometimes deliver twice - your handler must be safe to call repeatedly.
3. **Use `hmac.compare_digest`**, not `==` - prevents timing attacks.
4. **Return 200 fast.** Real work (DB writes, sending emails, calling agents) should be enqueued to a background worker. If the handler is slow, the sender times out and retries.

## Try it from curl

```bash
# Compute the signature
BODY='{"id":"evt_x","type":"test"}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "shh-this-is-secret" -r | cut -d' ' -f1)

curl -X POST http://127.0.0.1:8104/webhook \
  -H "content-type: application/json" \
  -H "x-signature: $SIG" \
  -d "$BODY"
```
