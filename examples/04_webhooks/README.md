# 04 - Webhooks (Stripe payment for a food delivery order)

Realistic scenario: Raj just paid 450 INR for chicken biryani via Stripe. Stripe POSTs `payment_intent.succeeded` to our backend. Our backend has to:

1. Verify it's actually from Stripe (not a fraudster)
2. Mark the order as paid in our DB
3. Notify the restaurant tablet that the order is good to cook
4. Send Raj an SMS confirmation
5. Hand back 200 within 5-10 seconds

This example simulates that full flow with 4 scenarios run back-to-back.

## What the receiver does

`POST /webhooks/stripe`:
- Verifies HMAC signature using `hmac.compare_digest` (timing-attack safe)
- Dedups by event id (Stripe sometimes delivers the same event twice)
- Switches on `event.type`:
  - `payment_intent.succeeded` -> marks the order paid, prints what the worker would do (notify restaurant, send SMS, trigger fulfillment agent)
  - `charge.refunded` -> marks the order refunded, prints worker actions
  - `payment_intent.payment_failed` -> logs, sends retry SMS
- Returns 200 fast

## Run

**Terminal 1** (the receiver - your backend):
```bash
cd examples/04_webhooks
uvicorn receiver:app --port 8104
```

**Terminal 2** (the sender - simulates Stripe):
```bash
cd examples/04_webhooks
python sender.py
```

## What you'll see

The sender prints 4 demos with REQUEST + RESPONSE + LESSON blocks. The receiver simultaneously logs:

```
[webhook]  ✓  ACCEPTED   event evt_pay_raj_001  type=payment_intent.succeeded
[worker ]              would: marked order order_raj_001 as paid in DB
[worker ]              would: notified restaurant tablet (order is now visible to kitchen)
[worker ]              would: sent SMS to Raj: 'Payment confirmed for Chicken Biryani, Raita'
[worker ]              would: triggered fulfillment agent
[webhook]  ~  DUPLICATE  event evt_pay_raj_001  (already processed, returning 200)
[webhook]  ✓  ACCEPTED   event evt_refund_raj_001  type=charge.refunded
[worker ]              would: marked order order_raj_001 as refunded
...
[webhook]  ✗  REJECTED  bad signature  (someone is trying to spoof events)
```

The four scenarios are:

1. **Valid payment** -> 200 OK, order marked paid, all downstream actions queued
2. **Same event again** -> 200 OK + `duplicate: true` (dedup worked)
3. **Refund** -> 200 OK, order marked refunded, restaurant notified
4. **Forged event** -> 401 Unauthorized (signature check stopped the attack)

## Talking points

- **Without signature verification**, anyone who knows the URL could `curl` `payment_intent.succeeded` for any order and we'd ship food we weren't paid for. Demo 4 is the live attack and our defense.
- **The handler is THIN.** Verify, dedup, "queue" (we just print), return 200. Real work happens in a worker process. If we'd done the work inline, Stripe's 5-10s timeout would fire under load and trigger retries.
- **Dedup matters more than people think.** Network blips, race conditions, and Stripe's own retry policy all cause double deliveries. Without dedup, you double-charge cards or double-send SMS. Both are bad customer experiences.
- **Return 200, NOT 5xx, for things you don't care about.** A 5xx tells Stripe to retry. Returning 200 + logging keeps your retries clean.

## Try it from curl

```bash
# Compute a valid signature
BODY='{"id":"evt_curl_test","type":"payment_intent.succeeded","data":{"object":{"metadata":{"order_id":"order_raj_001"}}}}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "whsec_demo_workshop_secret" -r | cut -d' ' -f1)

curl -X POST http://127.0.0.1:8104/webhooks/stripe \
  -H "content-type: application/json" \
  -H "stripe-signature: $SIG" \
  -d "$BODY"
```

## Where this pattern shows up

Every modern payment processor, every git host (PRs, pushes, merges), every messaging platform (Slack/Discord events), every CI provider (build status), every email service (SendGrid/SES delivery events) - all of these use webhooks shaped exactly like this. Once you've built one well, the rest are minor variations.
