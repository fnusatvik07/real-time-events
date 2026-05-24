# Project 3 - LiveOrder (the all-patterns-in-one capstone)

A single mini-app that uses **all four real-time patterns where each is actually the right tool for the job**. Unlike Project 1 (same chat, 3 ways) or Project 2 (one webhook pipeline), this project is what a real food-delivery app's backend might look like.

| Pattern | What we use it for |
|---------|---------------------|
| **Webhook** (HMAC-signed) | Stripe POSTs a payment event when the customer's card is charged |
| **SSE** | Live order status pushed to the customer (awaiting_payment -> paid -> cooking -> out for delivery -> delivered) |
| **WebSocket** | Customer ↔ driver chat tied to the order |
| **SSE** (token stream) | AI restaurant recommender (real OpenAI under the hood) |
| **Polling** | Long-running revenue report (batch job; UI polls until done) |

Five cards on one page, one running FastAPI server, every pattern labeled with its badge.

## Run

```bash
source /Users/datasense/Desktop/realtime/.venv/bin/activate
cd projects/project_3_liveorder
uvicorn server:app --reload --port 7000
```

Open http://localhost:7000

> Reads `OPENAI_API_KEY` from `../../.env` for the recommender card.

## End-to-end demo (90 seconds in class)

1. **Place an order.** Click "Place order" with default values (Raj, biryani, 450 INR). The SSE card connects; status shows "Waiting for payment".

2. **Simulate Stripe paying.** Click the red "Simulate Stripe payment" button in the Webhook card. Behind the scenes the server constructs a Stripe-shaped `payment_intent.succeeded` event, HMAC-signs it with the workshop secret, and POSTs it to its own `/webhooks/payment`. Watch:
   - **Webhook activity** card logs the event id.
   - **Order timeline** card jumps to "Payment confirmed via webhook" (SSE push).
   - Over the next ~21 seconds it auto-advances `paid -> cooking -> out for delivery -> delivered`. Each transition is one SSE event.

3. **Open chat as the driver.** Pick "As driver" in the chat card dropdown and click Connect. (You can also open this page in a second browser tab and connect as customer there.) Type messages back and forth; they appear instantly in both tabs over the WebSocket.

4. **Ask the AI recommender.** Type a question like "What's a quick spicy snack under 200 INR?" and click Ask. Watch the response stream in word-by-word — that's real OpenAI streaming relayed through your backend as SSE.

5. **Generate the revenue report.** Click "Generate today's revenue report". The status pill shows `pending -> running -> done` as the UI polls `/api/reports/{id}` every second. Result JSON renders when done.

6. **Open DevTools Network.** Each card has a distinct request shape:
   - Order card: one EventStream connection (SSE)
   - Webhook card: one POST (instant)
   - Chat card: one WS connection with frames
   - Recommender card: one POST that streams the body
   - Report card: many short polls every second until done

## Backend endpoints

```
POST /api/orders                        create an order (returns id)
GET  /api/orders/{id}                   one-shot snapshot
GET  /api/orders/{id}/stream            SSE - status changes, webhooks, chat msgs

POST /webhooks/payment                  Stripe-style HMAC-signed event
POST /api/simulate/payment/{order_id}   fires a signed event at our own webhook
                                        (so demo works without ngrok / Stripe)

WS   /api/chat/{order_id}?role=...      bidirectional chat (customer | driver)

POST /api/recommend                     SSE stream of OpenAI response
POST /api/reports/revenue               kick a long-running report; returns job_id
GET  /api/reports/{id}                  poll for status + result

GET  /api/about                         lists everything above
```

## Order state machine

```
awaiting_payment
   │  (webhook payment_intent.succeeded arrives)
   ▼
paid                                                  ─ webhook trigger
   │  3s
   ▼
restaurant_confirmed                                  ┐
   │  5s                                              │
   ▼                                                  │
cooking                                               ├─ background coroutine
   │  5s                                              │   auto-advances
   ▼                                                  │
out_for_delivery                                      │
   │  8s                                              │
   ▼                                                  ┘
delivered
```

Each transition fires an SSE `event: status` to every subscriber on `/api/orders/{id}/stream`.

## Why this exists (vs Projects 1 and 2)

| Project | Teaches |
|---------|---------|
| **Project 1** | The SAME thing 3 ways. Compare polling vs SSE vs WebSocket UX side-by-side. |
| **Project 2** | Webhook intake done correctly (HMAC, dedup, fast 200) + receiving-side polling vs SSE comparison. |
| **Project 3** (this) | All 4 patterns composing one realistic app, each used where it actually fits. The "capstone" you'd fork to start a real app. |

## Source

- `server.py` — ~400 lines, every section commented, all 5 patterns in one file
- `static/index.html` — ~500 lines, vanilla JS, no framework. One page, five cards.

## What you might tweak after forking

- **Persist orders / chat / events** to a real database (currently in-memory). Replace `orders: dict[str, Order]` with rows in Postgres, the chat broadcaster with Redis pub-sub.
- **Add auth** — currently anyone can place an order or join any chat room. Drop in JWT verification on the WebSocket connect and the POST endpoints (see Example 01 for the pattern).
- **Real Stripe webhooks** — point a real Stripe webhook at `/webhooks/payment` via ngrok. The HMAC verification already matches Stripe's scheme (modulo the timestamp; trivial addition).
- **Real driver-matching** — replace the auto-advance coroutine with a real matching service that fires the `restaurant_confirmed` and `out_for_delivery` events.
