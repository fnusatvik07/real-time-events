# Project 2: Webhook-Driven Live Dashboard

A complete event pipeline showing **three patterns working together**:

```
[external service]  --webhook POST-->  [your backend]  --SSE push-->   [dashboard]
   (Stripe etc.)     signed + dedup     verify, store,    live          (also:
                                        broadcast         updates        polling
                                                                         fallback)
```

## What this demonstrates

- **Webhook intake done correctly:** HMAC signature verification, idempotent dedup by event id, fast 200 OK.
- **Polling vs SSE on the receiving side:** same event feed, two dashboards. Open Chrome DevTools and watch the network panel.
- **Idempotency / replay protection** with a "send duplicate" simulator.
- **Forgery protection** with a "send unsigned" simulator.

## Run it

```bash
source .venv/bin/activate
cd projects/project_2_webhook_dashboard
uvicorn server:app --reload --port 9000
```

Open http://localhost:9000

## How to demo in class

1. **Open the page + DevTools → Network.** Note the polling dashboard fires a request every 2s; the SSE dashboard has ONE connection sitting open.
2. **Click "+1 event"** - SSE shows it instantly, polling waits for next tick.
3. **Click "+5 events"** - both update.
4. **Click "Send duplicate"** - show the server response: `{first: {ok:true, seq:N}, second: {ok:true, duplicate:true}}`. Dashboard only shows it once.
5. **Click "Send unsigned"** - server returns HTTP 401, nothing appears.
6. **Click "Disconnect" on SSE side, then fire 3 events, then "Reconnect".** The reconnected client gets all 3 events it missed (catch-up replay).

## Endpoints

```
POST /webhook/payment           ← external services POST signed events here
GET  /events?since=N            ← polling endpoint, returns events with seq > N
GET  /stream?since=N            ← SSE endpoint, replays from N then pushes live

POST /simulate/burst?n=5        ← fire N fake webhooks at ourselves
POST /simulate/replay           ← send same event twice (dedup test)
POST /simulate/forgery          ← send unsigned event (signature test)
POST /admin/reset               ← wipe SQLite DB
```

## What's in the wire

A webhook in:
```
POST /webhook/payment
X-Signature: hmac_sha256(secret, body)
{
  "id": "evt_abc123",
  "type": "payment.succeeded",
  "data": {"customer": "Alice", "amount_cents": 5000, "currency": "USD"}
}
```

An SSE event out:
```
id: 42
event: payment
data: {"seq":42,"event_id":"evt_abc123","type":"payment.succeeded",...}

```

## Try it with a real webhook sender

Add the `Stripe-Signature`-style HMAC and you can point real Stripe test webhooks at this endpoint via ngrok:
```bash
ngrok http 9000
# then in Stripe dashboard, set webhook URL to https://xxx.ngrok.io/webhook/payment
```

(Stripe uses a slightly different signature scheme with timestamps - see `concepts/03_webhooks.md`.)

## Source

- `server.py` - backend, ~250 lines, every section commented
- `static/index.html` - dashboard, vanilla JS, side-by-side comparison
- `events.db` - auto-created SQLite store
