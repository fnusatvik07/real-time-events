# Postman Collection

A fully wired Postman collection covering every HTTP endpoint across the 7 examples and 2 projects in this workshop. Import once, click "Send" on any request, see the response.

**Stats:** 8 folders, 43 requests, 18 collection variables.

## Import

1. Open Postman.
2. **File -> Import** (or Ctrl/Cmd+O).
3. Drop `real-time-workshop.postman_collection.json` in.
4. You'll see a new collection in the left sidebar called "Real-Time Patterns Workshop" with 8 folders.

## Use

Before clicking "Send" on a request, start the matching server in a terminal. Each folder's description lists the command (it's also in the table below).

| Folder | Start the server with |
|--------|-----------------------|
| 01 - HTTP basics             | `cd examples/01_http_basics && uvicorn server:app --port 8101` |
| 02 - Short polling           | `cd examples/02_short_polling && uvicorn server:app --port 8102` |
| 03 - Long polling            | `cd examples/03_long_polling && uvicorn server:app --port 8103` |
| 04 - Webhooks                | `cd examples/04_webhooks && uvicorn receiver:app --port 8104` |
| 05 - SSE                     | `cd examples/05_sse && uvicorn server:app --port 8105` |
| 06 - WebSockets              | `cd examples/06_websockets && uvicorn server:app --port 8106` |
| Project 1 - Streaming chat   | `cd projects/project_1_streaming_chat && uvicorn server:app --port 8000` |
| Project 2 - Webhook dashboard | `cd projects/project_2_webhook_dashboard && uvicorn server:app --port 9000` |

## What the collection does for you

### Pre-request scripts handle the cryptography

- **Example 01 -> "GET /me with VALID JWT"** runs a pre-request script that builds a real HS256 JWT for `Arjun Kumar` (sub, name, email, iat, exp, scope claims) using the workshop's shared secret, then sends it in the `Authorization: Bearer <jwt>` header.

- **Example 01 -> "GET /me with TAMPERED JWT"** builds a valid JWT, then swaps the `name` claim from `Arjun Kumar` to `Hacker Admin` but keeps the original signature. The server rejects with 401. This proves the signature verification works.

- **Example 04 webhook requests** HMAC-sign the request body and set the `x-signature` / `stripe-signature` headers automatically. You don't have to compute anything.

### Variables chain together

Several requests stash returned ids in collection variables so the next request picks them up automatically:

- `POST /notes` saves `{{last_note_id}}` -> `GET /notes/{{last_note_id}}` uses it
- `POST /orders` saves `{{last_order_id}}` -> `GET /orders/{{last_order_id}}` uses it
- `POST /rides` saves `{{last_ride_id}}` -> `GET /rides/{{last_ride_id}}/wait` uses it
- `POST /api/polling/start` saves `{{polling_job_id}}` -> the status and result requests use it

So you can run the requests **top to bottom in a folder** and they'll just work.

## Things worth trying

### Watch a long-poll hang in Postman

Open Example 03 -> `GET /rides/{{last_ride_id}}/wait`. Click Send. **Watch the spinner spin for ~4-12 seconds** before the response appears. That's the server holding the request open until a driver accepts. Compare to a normal request which returns in milliseconds. This is the entire long-polling pattern in one click.

### See dedup work

Example 04 -> `POST /webhooks/stripe (2) DUPLICATE delivery`. Click Send twice in a row. First response: `"duplicate": false`. Second response: `"duplicate": true`. The server processed the event once and now refuses to process it again.

### See signature verification stop forgery

Example 04 -> `POST /webhooks/stripe (4) FORGED event`. The hardcoded fake signature won't match what the server computes. Returns 401. This is the demo for why webhook signatures matter.

### Watch SSE stream into Postman

Example 05 -> `POST /chat`. Click Send. The response body grows in real-time as the server streams ~50 word events back. Switch the response viewer to **Raw** to see the SSE wire format (`id:` / `event:` / `data:` / blank line, repeated).

### Subscribe to a live SSE feed and trigger events from another tab

Project 2 -> `GET /stream?since=0` in one Postman tab (keeps the connection open). In another tab, hit `POST /simulate/burst?n=5`. Watch the events appear in the stream tab in real-time.

## WebSockets

Postman supports WebSockets but as a **separate request type** (HTTP requests can't open WS connections). To test the chat in Example 06 or Project 1's WS endpoint:

1. **File -> New -> WebSocket Request**
2. Paste a URL, click **Connect**:
   - `ws://127.0.0.1:8106/chat?role=customer&order=order_raj_001`
   - `ws://127.0.0.1:8106/chat?role=driver&order=order_raj_001`
   - `ws://127.0.0.1:8000/api/ws/chat` (Project 1)
3. Send messages as text (JSON payloads). For example:
   ```json
   {"type": "msg", "text": "hello from postman"}
   {"type": "typing", "on": true}
   ```
4. Open a second WebSocket tab with the other role to chat both ways.

## Regenerating the collection

If you tweak the examples and want to update the collection:

```bash
cd postman
python _build.py
```

This regenerates `real-time-workshop.postman_collection.json` from `_build.py`. Re-import into Postman (or use Postman's "Update" prompt if it detects changes).

## Secrets in the collection

The shared secrets in the variables are **demo-only** and intentionally non-secret:

| Variable | Used by |
|----------|---------|
| `jwt_secret` | Example 01 - signs the demo JWT |
| `webhook_secret` | Example 04 - HMAC for webhook bodies |
| `webhook_secret_p2` | Project 2 - HMAC for webhook bodies |

In a real deployment these would be loaded from a secret manager. Don't reuse them anywhere that matters.
