"""Generate the Postman collection JSON from a Python definition.

Doing this in Python (instead of hand-editing 3,000 lines of JSON) keeps
the collection in sync with the code as we evolve the examples.

Run:
    python _build.py

Output:
    real-time-workshop.postman_collection.json
"""
from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent

HERE = Path(__file__).parent
OUT = HERE / "real-time-workshop.postman_collection.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def url(raw: str) -> dict:
    """Build a properly-structured Postman v2.1 URL object.

    Postman's UI reads `host`, `path`, `port`, and `query` fields - NOT
    just `raw`. If you only set `raw`, the URL bar shows blank and the
    query params tab is empty. Build the structured fields too.
    """
    # Split off query string
    if "?" in raw:
        path_part, query_str = raw.split("?", 1)
    else:
        path_part, query_str = raw, ""

    # Detect host. Two forms we use:
    #   {{base_NNNN}}/some/path     -> host = ["{{base_NNNN}}"]
    #   http://127.0.0.1:NNNN/path  -> host = ["127.0.0.1"], port = "NNNN"
    if path_part.startswith("{{"):
        end = path_part.find("}}") + 2
        host_part = path_part[:end]
        rest = path_part[end:]
        port = None
    elif "://" in path_part:
        scheme_end = path_part.find("://") + 3
        next_slash = path_part.find("/", scheme_end)
        if next_slash == -1:
            host_with_port = path_part[scheme_end:]
            rest = ""
        else:
            host_with_port = path_part[scheme_end:next_slash]
            rest = path_part[next_slash:]
        if ":" in host_with_port:
            host_part, port = host_with_port.rsplit(":", 1)
        else:
            host_part, port = host_with_port, None
    else:
        host_part = path_part
        rest = ""
        port = None

    # Path segments: split on "/", drop leading empty from the leading slash.
    if rest.startswith("/"):
        rest = rest[1:]
    if rest == "":
        path_segments: list[str] = [""]   # represents trailing slash
    else:
        path_segments = rest.split("/")

    obj: dict = {
        "raw": raw,
        "host": [host_part],
        "path": path_segments,
    }
    if port:
        obj["port"] = port

    if query_str:
        obj["query"] = []
        for pair in query_str.split("&"):
            if "=" in pair:
                k, v = pair.split("=", 1)
            else:
                k, v = pair, ""
            obj["query"].append({"key": k, "value": v})

    return obj


def req(method: str, raw_url: str, *,
        body: dict | None = None,
        headers: list[tuple[str, str]] | None = None,
        description: str = "",
        pre_script: str | None = None,
        test_script: str | None = None) -> dict:
    """Build a Postman item (request) entry."""
    item: dict = {
        "name": "",  # filled in by caller via wrap()
        "request": {
            "method": method,
            "header": [{"key": k, "value": v} for k, v in (headers or [])],
            "url": url(raw_url),
        },
    }
    if description:
        item["request"]["description"] = description
    if body is not None:
        item["request"]["body"] = {
            "mode": "raw",
            "raw": json.dumps(body, indent=2),
            "options": {"raw": {"language": "json"}},
        }
    events = []
    if pre_script:
        events.append({
            "listen": "prerequest",
            "script": {"exec": pre_script.strip().splitlines(), "type": "text/javascript"},
        })
    if test_script:
        events.append({
            "listen": "test",
            "script": {"exec": test_script.strip().splitlines(), "type": "text/javascript"},
        })
    if events:
        item["event"] = events
    return item


def named(name: str, item: dict) -> dict:
    item["name"] = name
    return item


def folder(name: str, description: str, items: list[dict]) -> dict:
    return {
        "name": name,
        "description": description,
        "item": items,
    }


# ---------------------------------------------------------------------------
# Pre-request scripts (run by Postman before each request)
# ---------------------------------------------------------------------------

# Builds a JWT for Arjun and stashes it in the collection variable {{arjun_jwt}}.
# Used by example 01 demo 4 call B.
BUILD_JWT_SCRIPT = """
// Build an HS256 JWT for user Arjun using the workshop's shared secret.
var secret = pm.collectionVariables.get("jwt_secret");
function b64url(wordArray) {
    return CryptoJS.enc.Base64.stringify(wordArray)
        .replace(/=+$/, '').replace(/\\+/g, '-').replace(/\\//g, '_');
}
function b64urlStr(str) {
    return b64url(CryptoJS.enc.Utf8.parse(str));
}
var header = b64urlStr(JSON.stringify({alg: "HS256", typ: "JWT"}));
var now = Math.floor(Date.now() / 1000);
var claims = {
    sub: "usr_arjun_8c3d2",
    name: "Arjun Kumar",
    email: "arjun.kumar@liveorder.app",
    iat: now,
    exp: now + 3600,
    scope: ["orders:read", "orders:write"]
};
var payload = b64urlStr(JSON.stringify(claims));
var sigBytes = CryptoJS.HmacSHA256(header + "." + payload, secret);
var jwt = header + "." + payload + "." + b64url(sigBytes);
pm.collectionVariables.set("arjun_jwt", jwt);
console.log("Set {{arjun_jwt}} =", jwt);
"""

# Builds a tampered JWT (modifies the 'name' claim but keeps the old signature
# so the server will reject it).
BUILD_TAMPERED_JWT_SCRIPT = """
// Build a JWT, then tamper with the payload but reuse the original signature.
// The server will recompute the signature on the new payload and reject.
var secret = pm.collectionVariables.get("jwt_secret");
function b64url(wordArray) {
    return CryptoJS.enc.Base64.stringify(wordArray)
        .replace(/=+$/, '').replace(/\\+/g, '-').replace(/\\//g, '_');
}
function b64urlStr(str) {
    return b64url(CryptoJS.enc.Utf8.parse(str));
}
var header = b64urlStr(JSON.stringify({alg: "HS256", typ: "JWT"}));
var now = Math.floor(Date.now() / 1000);
var validClaims = {sub:"usr_arjun_8c3d2", name:"Arjun Kumar",
    email:"arjun.kumar@liveorder.app", iat: now, exp: now+3600,
    scope:["orders:read","orders:write"]};
var validPayload = b64urlStr(JSON.stringify(validClaims));
var realSig = b64url(CryptoJS.HmacSHA256(header + "." + validPayload, secret));

// Now build a TAMPERED payload (name changed) but keep the OLD signature
var evilClaims = Object.assign({}, validClaims, {name: "Hacker Admin", scope: ["admin"]});
var evilPayload = b64urlStr(JSON.stringify(evilClaims));
var tampered = header + "." + evilPayload + "." + realSig;
pm.collectionVariables.set("tampered_jwt", tampered);
console.log("Set {{tampered_jwt}} =", tampered);
"""

# Signs the request body with the webhook secret. Used for example 04 + project 2.
SIGN_WEBHOOK_SCRIPT = """
// HMAC-SHA256 sign the raw body with the webhook shared secret. The signature
// goes in the x-signature (or stripe-signature) header.
var secret = pm.collectionVariables.get("webhook_secret");
var body = pm.request.body && pm.request.body.raw ? pm.request.body.raw : "";
var signature = CryptoJS.HmacSHA256(body, secret).toString();
pm.request.headers.upsert({key: "x-signature", value: signature});
pm.request.headers.upsert({key: "stripe-signature", value: signature});
console.log("Signed body, signature =", signature);
"""

# Generates a unique event id so each "send" creates a fresh event in the
# webhook receiver (otherwise dedup returns duplicate:true on the second send).
NEW_EVENT_ID_SCRIPT = """
// Generate a unique event id so dedup doesn't kick in. To deliberately test
// dedup, use the "duplicate delivery" request which uses a FIXED id.
var randomId = "evt_pm_" + Date.now() + "_" + Math.floor(Math.random()*1000);
pm.collectionVariables.set("event_id", randomId);
"""


# ---------------------------------------------------------------------------
# Folder: 01 - HTTP basics  (port 8101)
# ---------------------------------------------------------------------------
folder_01 = folder(
    "01 - HTTP basics (port 8101)",
    "Realistic mini-backend: notes, JWT auth (real HS256), external API call to wttr.in. "
    "Start the server first:\n\n    cd examples/01_http_basics && uvicorn server:app --port 8101",
    [
        named("GET /", req("GET", "{{base_8101}}/",
            description="Lists every endpoint this server exposes.")),

        named("GET /time", req("GET", "{{base_8101}}/time",
            description="Pure read - returns server's clock. No state.")),

        named("GET /counter (call 3x to see it increment)",
            req("GET", "{{base_8101}}/counter",
                description="A SHARED counter. Important teaching point: the server has DATA "
                            "(the counter goes up) but no memory of YOU specifically. Anyone "
                            "calling this same endpoint bumps the same number.")),

        named("GET /me  (no auth -> 401)",
            req("GET", "{{base_8101}}/me",
                description="No Authorization header. Server returns 401 with a clue about "
                            "what header to send.")),

        named("GET /me  (with VALID JWT for Arjun)",
            req("GET", "{{base_8101}}/me",
                headers=[("Authorization", "Bearer {{arjun_jwt}}")],
                pre_script=BUILD_JWT_SCRIPT,
                description="Builds a real HS256 JWT for user 'Arjun Kumar' before sending. "
                            "Server verifies the signature and returns decoded claims "
                            "(user_id, name, email, scopes).")),

        named("GET /me  (with TAMPERED JWT -> 401)",
            req("GET", "{{base_8101}}/me",
                headers=[("Authorization", "Bearer {{tampered_jwt}}")],
                pre_script=BUILD_TAMPERED_JWT_SCRIPT,
                description="Builds a JWT, modifies the 'name' claim to 'Hacker Admin', but "
                            "keeps the original signature. The server recomputes the signature "
                            "over the new payload, finds it doesn't match, and returns 401. "
                            "This is the whole reason JWTs work.")),

        named("GET /weather/Bengaluru  (real external API call)",
            req("GET", "{{base_8101}}/weather/Bengaluru",
                description="The server calls https://wttr.in/Bengaluru and returns a slimmed-down "
                            "weather response. Demonstrates that real backends are mostly glue "
                            "between other backends.")),

        named("GET /weather/Mumbai", req("GET", "{{base_8101}}/weather/Mumbai")),

        named("POST /notes  (create)",
            req("POST", "{{base_8101}}/notes",
                body={"title": "Buy biryani for dinner", "user": "Arjun"},
                description="Creates a note. Returns 201 Created with the created resource. "
                            "Save the returned `id` and use it in 'GET /notes/{id}' below.",
                test_script="""
var note = pm.response.json();
pm.collectionVariables.set("last_note_id", note.id);
console.log("saved last_note_id =", note.id);
""")),

        named("GET /notes  (list all)",
            req("GET", "{{base_8101}}/notes",
                description="Lists all notes currently in memory.")),

        named("GET /notes/{{last_note_id}}  (fetch the one we just created)",
            req("GET", "{{base_8101}}/notes/{{last_note_id}}",
                description="Fetches the note from the POST above. The POST stored "
                            "{{last_note_id}} for us.")),

        named("GET /notes/9999  (404)",
            req("GET", "{{base_8101}}/notes/9999",
                description="Non-existent id - server returns 404 Not Found.")),
    ],
)


# ---------------------------------------------------------------------------
# Folder: 02 - Short polling  (port 8102)
# ---------------------------------------------------------------------------
folder_02 = folder(
    "02 - Short polling - Swiggy order tracker (port 8102)",
    "A food-delivery order progresses through realistic stages over ~40 seconds. "
    "Use 'POST /orders' to create one, then poll 'GET /orders/{id}' on a fast loop "
    "and watch the status advance.\n\n"
    "Start the server first:\n\n    cd examples/02_short_polling && uvicorn server:app --port 8102",
    [
        named("GET /", req("GET", "{{base_8102}}/",
            description="Info page - lists endpoints and the order stages.")),

        named("POST /orders  (place an order)",
            req("POST", "{{base_8102}}/orders",
                body={"customer": "Raj", "item": "Chicken Biryani", "amount_inr": 450},
                description="Creates an order and kicks off the background state-machine. "
                            "Saves {{last_order_id}} for the next request.",
                test_script="""
var o = pm.response.json();
pm.collectionVariables.set("last_order_id", o.id);
console.log("saved last_order_id =", o.id);
""")),

        named("GET /orders/{{last_order_id}}  (poll once)",
            req("GET", "{{base_8102}}/orders/{{last_order_id}}",
                description="Returns the current order status. In real life the client would "
                            "send this on a timer (every 1-2s) and watch for status changes.")),

        named("GET /orders  (list all)",
            req("GET", "{{base_8102}}/orders",
                description="Debug: list all in-memory orders.")),
    ],
)


# ---------------------------------------------------------------------------
# Folder: 03 - Long polling  (port 8103)
# ---------------------------------------------------------------------------
folder_03 = folder(
    "03 - Long polling - Uber ride dispatch (port 8103)",
    "Create a ride, then long-poll for a driver to accept. The long-poll request will hang "
    "for 4-12 seconds and return the moment a driver is matched.\n\n"
    "Start the server first:\n\n    cd examples/03_long_polling && uvicorn server:app --port 8103",
    [
        named("GET /", req("GET", "{{base_8103}}/", description="Info page.")),

        named("POST /rides  (request a ride)",
            req("POST", "{{base_8103}}/rides",
                body={"rider": "Raj", "pickup": "Indiranagar Metro", "dropoff": "Airport"},
                description="Creates a ride and kicks off a background driver matcher.",
                test_script="""
var r = pm.response.json();
pm.collectionVariables.set("last_ride_id", r.id);
console.log("saved last_ride_id =", r.id);
""")),

        named("GET /rides/{{last_ride_id}}  (current snapshot)",
            req("GET", "{{base_8103}}/rides/{{last_ride_id}}",
                description="Quick snapshot - shows whether a driver has been matched yet.")),

        named("GET /rides/{{last_ride_id}}/wait  (LONG POLL - will hang 4-12s)",
            req("GET", "{{base_8103}}/rides/{{last_ride_id}}/wait?timeout=30",
                description="THIS IS THE INTERESTING ONE. The server will hold the request open "
                            "until a driver accepts. You'll see Postman's spinner spin for a few "
                            "seconds, then suddenly the response appears with full driver info "
                            "(name, vehicle, rating, ETA). Increase Postman's request timeout "
                            "to 60s+ in Settings if needed.")),

        named("GET /rides/{{last_ride_id}}/wait?timeout=2  (force a timeout)",
            req("GET", "{{base_8103}}/rides/{{last_ride_id}}/wait?timeout=2",
                description="Short server-side timeout to demonstrate the timed_out:true return. "
                            "If the ride was already accepted, this returns immediately.")),
    ],
)


# ---------------------------------------------------------------------------
# Folder: 04 - Webhooks  (port 8104)
# ---------------------------------------------------------------------------
folder_04 = folder(
    "04 - Webhooks - Stripe payment for biryani (port 8104)",
    "Send signed webhook events to a food-delivery backend. Each request has a pre-request "
    "script that HMAC-signs the body with the workshop secret.\n\n"
    "Start the receiver first:\n\n    cd examples/04_webhooks && uvicorn receiver:app --port 8104\n\n"
    "Watch the receiver's terminal too - it prints what the downstream worker would do "
    "(notify restaurant, send SMS, etc).",
    [
        named("GET /", req("GET", "{{base_8104}}/",
            description="Info page + list of orders + count of events seen so far.")),

        named("GET /orders  (current state of orders DB)",
            req("GET", "{{base_8104}}/orders")),

        named("POST /webhooks/stripe  (1) valid payment.succeeded",
            req("POST", "{{base_8104}}/webhooks/stripe",
                headers=[("content-type", "application/json")],
                pre_script=NEW_EVENT_ID_SCRIPT + SIGN_WEBHOOK_SCRIPT,
                body={
                    "id": "{{event_id}}",
                    "type": "payment_intent.succeeded",
                    "created": 1700000000,
                    "data": {
                        "object": {
                            "id": "pi_test123",
                            "amount": 45000,
                            "currency": "inr",
                            "customer": "cus_raj",
                            "metadata": {"order_id": "order_raj_001"},
                        }
                    },
                },
                description="Properly signed event. Server marks the order paid, notifies the "
                            "restaurant, queues an SMS. Returns 200 with duplicate:false.")),

        named("POST /webhooks/stripe  (2) DUPLICATE delivery (test dedup)",
            req("POST", "{{base_8104}}/webhooks/stripe",
                headers=[("content-type", "application/json")],
                pre_script=SIGN_WEBHOOK_SCRIPT,  # uses FIXED event_id below
                body={
                    "id": "evt_postman_fixed_for_dedup_test",
                    "type": "payment_intent.succeeded",
                    "created": 1700000000,
                    "data": {"object": {"id": "pi_fixed", "amount": 45000, "currency": "inr",
                                         "customer": "cus_raj", "metadata": {"order_id": "order_raj_001"}}},
                },
                description="HARD-CODED event id. Send this TWICE. First time: 200 with "
                            "duplicate:false. Second time: 200 with duplicate:true - the dedup "
                            "logic stops us from double-processing.")),

        named("POST /webhooks/stripe  (3) charge.refunded",
            req("POST", "{{base_8104}}/webhooks/stripe",
                headers=[("content-type", "application/json")],
                pre_script=NEW_EVENT_ID_SCRIPT + SIGN_WEBHOOK_SCRIPT,
                body={
                    "id": "{{event_id}}",
                    "type": "charge.refunded",
                    "created": 1700000100,
                    "data": {"object": {"id": "ch_xyz", "amount_refunded": 45000,
                                         "metadata": {"order_id": "order_raj_001"}}},
                },
                description="A refund event for the same order. Receiver marks it refunded "
                            "and would tell the restaurant to cancel prep.")),

        named("POST /webhooks/stripe  (4) FORGED event (bad signature -> 401)",
            req("POST", "{{base_8104}}/webhooks/stripe",
                headers=[
                    ("content-type", "application/json"),
                    ("x-signature", "deadbeef_obviously_fake_signature"),
                ],
                body={
                    "id": "evt_attacker_001",
                    "type": "payment_intent.succeeded",
                    "data": {"object": {"id": "pi_fake", "amount": 9999999, "currency": "inr",
                                         "customer": "cus_attacker", "metadata": {"order_id": "order_raj_001"}}},
                },
                description="No pre-request signing script. The hardcoded fake signature won't "
                            "match anything the server computes -> 401. This is the demonstration "
                            "that signature verification is what stops fraudsters.")),
    ],
)


# ---------------------------------------------------------------------------
# Folder: 05 - SSE  (port 8105)
# ---------------------------------------------------------------------------
folder_05 = folder(
    "05 - SSE - real LLM stream relayed through your backend (port 8105)",
    "Send a prompt; your local backend calls OpenAI with stream=True and relays each chunk "
    "back to you as an SSE event. This is the exact pattern Vercel AI SDK uses: browser "
    "speaks to YOUR domain over SSE, your backend speaks to OpenAI over SSE. The API key "
    "never leaves your server.\n\n"
    "Start the server first:\n\n    cd examples/05_sse && uvicorn server:app --port 8105\n\n"
    "Requires OPENAI_API_KEY in ../../.env.\n\n"
    "Tip: in Postman, set the response viewer to 'Raw' to see the SSE wire format "
    "(id: / event: / data: / blank line, repeated). Tokens will appear one at a time as "
    "the model generates them.",
    [
        named("GET /", req("GET", "{{base_8105}}/",
            description="Info page. Also confirms whether OPENAI_API_KEY is configured "
                        "(openai_key_configured: true|false).")),

        named("POST /chat  (real LLM stream - 3 Mumbai street foods)",
            req("POST", "{{base_8105}}/chat",
                headers=[
                    ("content-type", "application/json"),
                    ("accept", "text/event-stream"),
                ],
                body={"prompt": "What are 3 must-try Mumbai street foods? One short paragraph per dish."},
                description="Real call to OpenAI gpt-4o-mini, streamed through your backend. "
                            "Postman will show the response body growing in real-time as the "
                            "model generates each token. Watch the events:\n\n"
                            "  event: open    once at the start, payload includes prompt + model\n"
                            "  event: token   one per chunk, payload is {text, index}\n"
                            "  event: done    once at the end, payload is {token_count}\n\n"
                            "If you see event: error instead, OPENAI_API_KEY is missing or invalid.")),

        named("POST /chat  (real LLM stream - custom prompt)",
            req("POST", "{{base_8105}}/chat",
                headers=[
                    ("content-type", "application/json"),
                    ("accept", "text/event-stream"),
                ],
                body={"prompt": "Recommend a cheap vegetarian dinner under 300 INR in Bengaluru."},
                description="Same endpoint with a different prompt. Edit the body to try your "
                            "own prompts and watch them stream back live.")),
    ],
)


# ---------------------------------------------------------------------------
# Folder: 06 - WebSockets  (port 8106)
# ---------------------------------------------------------------------------
# Postman supports WebSocket requests but they're a separate type. The collection
# JSON can still include HTTP introspection endpoints. For the actual WS chat,
# we document the URL in the README and the user opens a "New > WebSocket Request"
# in Postman with that URL.
folder_06 = folder(
    "06 - WebSockets - delivery chat (port 8106)",
    "WebSocket-based two-way chat between a delivery driver and a customer.\n\n"
    "Start the server first:\n\n    cd examples/06_websockets && uvicorn server:app --port 8106\n\n"
    "FOR THE ACTUAL CHAT (HTTP requests can't open WS):\n"
    "Use Postman's WebSocket Request type: File -> New -> WebSocket Request.\n"
    "Paste a URL, click Connect:\n\n"
    "    ws://127.0.0.1:8106/chat?role=customer&order=order_raj_001\n\n"
    "Open a second WebSocket Request in another tab with role=driver. Now you can type "
    "messages in either tab and watch them appear in the other - real bidirectional "
    "chat over one TCP connection.\n\n"
    "Send these JSON payloads as text from either tab:\n"
    '    {\"type\": \"msg\", \"text\": \"hi from postman\"}\n'
    '    {\"type\": \"typing\", \"on\": true}\n\n'
    "The HTTP requests in this folder are just for inspecting state - the actual "
    "demo lives in the WebSocket tabs above.",
    [
        named("GET /", req("GET", "{{base_8106}}/",
            description="Info page + example WS URLs to paste into Postman's WebSocket Request.")),

        named("GET /sessions  (debug: list active chat rooms)",
            req("GET", "{{base_8106}}/sessions",
                description="Lists the in-memory rooms and which roles are connected to each. "
                            "Useful for confirming both your customer and driver WS tabs joined "
                            "the same order id.")),
    ],
)


# ---------------------------------------------------------------------------
# Folder: Project 1 - streaming chat  (port 8000)
# ---------------------------------------------------------------------------
folder_p1 = folder(
    "Project 1 - Streaming chat (port 8000)",
    "Same LLM chat call exposed 3 ways: polling, SSE, WebSocket.\n\n"
    "Start the server first:\n\n    cd projects/project_1_streaming_chat && uvicorn server:app --port 8000\n\n"
    "Browser UI is at http://localhost:8000 - this collection lets you poke the API directly.",
    [
        named("GET /api/about",
            req("GET", "{{base_8000}}/api/about",
                description="Lists all 3 patterns and their endpoints.")),

        named("POST /api/polling/start  (kick a job)",
            req("POST", "{{base_8000}}/api/polling/start",
                body={"prompt": "Recommend a quick vegetarian dinner in Bengaluru"},
                description="Returns a job_id. Save it for the polling status endpoint.",
                test_script="""
var j = pm.response.json();
pm.collectionVariables.set("polling_job_id", j.job_id);
console.log("saved polling_job_id =", j.job_id);
""")),

        named("GET /api/polling/status/{{polling_job_id}}",
            req("GET", "{{base_8000}}/api/polling/status/{{polling_job_id}}",
                description="Poll this every second until status is 'done'. Then fetch the result.")),

        named("GET /api/polling/result/{{polling_job_id}}",
            req("GET", "{{base_8000}}/api/polling/result/{{polling_job_id}}",
                description="Returns 409 if the job isn't done yet. 200 with the response text once it is.")),

        named("POST /api/sse/chat  (streams tokens over SSE)",
            req("POST", "{{base_8000}}/api/sse/chat",
                headers=[
                    ("content-type", "application/json"),
                    ("accept", "text/event-stream"),
                ],
                body={"prompt": "Tell me a 100-word story about a robot and biryani."},
                description="Postman will show the streaming response body filling in word-by-word.")),
    ],
)


# ---------------------------------------------------------------------------
# Folder: Project 2 - webhook dashboard  (port 9000)
# ---------------------------------------------------------------------------
folder_p2 = folder(
    "Project 2 - Webhook dashboard (port 9000)",
    "Webhook intake + SQLite + live SSE dashboard. Browser UI at http://localhost:9000.\n\n"
    "Start the server first:\n\n    cd projects/project_2_webhook_dashboard && uvicorn server:app --port 9000",
    [
        named("POST /admin/reset  (clear DB)",
            req("POST", "{{base_9000}}/admin/reset")),

        named("POST /simulate/burst?n=5  (fire 5 fake events at our own webhook)",
            req("POST", "{{base_9000}}/simulate/burst?n=5",
                description="Server-side helper that POSTs 5 properly-signed events at "
                            "/webhook/payment. Each appears live in any open /stream subscriber.")),

        named("POST /simulate/replay  (send same event twice -> dedup)",
            req("POST", "{{base_9000}}/simulate/replay")),

        named("POST /simulate/forgery  (send unsigned -> 401)",
            req("POST", "{{base_9000}}/simulate/forgery")),

        named("GET /events?since=0  (polling endpoint)",
            req("GET", "{{base_9000}}/events?since=0",
                description="Returns events with seq > since. The polling dashboard uses "
                            "this on a 2-second loop.")),

        named("GET /stream?since=0  (SSE live push)",
            req("GET", "{{base_9000}}/stream?since=0",
                headers=[("accept", "text/event-stream")],
                description="Subscribe to the live event stream. Postman will keep this open "
                            "and show new events as they arrive. Fire a burst from another tab "
                            "to see events appear here in real-time.")),

        named("POST /webhook/payment  (signed event directly)",
            req("POST", "{{base_9000}}/webhook/payment",
                headers=[("content-type", "application/json")],
                pre_script=NEW_EVENT_ID_SCRIPT + """
// Project 2 expects x-signature, not stripe-signature
var secret = pm.collectionVariables.get("webhook_secret_p2");
var body = pm.request.body && pm.request.body.raw ? pm.request.body.raw : "";
var signature = CryptoJS.HmacSHA256(body, secret).toString();
pm.request.headers.upsert({key: "x-signature", value: signature});
""",
                body={
                    "id": "{{event_id}}",
                    "type": "payment.succeeded",
                    "data": {"customer": "Raj", "amount_cents": 45000, "currency": "INR"},
                },
                description="Send a signed event directly (instead of using the burst simulator). "
                            "Uses project 2's webhook_secret_p2.")),
    ],
)


# ---------------------------------------------------------------------------
# Top-level collection
# ---------------------------------------------------------------------------
collection = {
    "info": {
        "_postman_id": "real-time-workshop",
        "name": "Real-Time Patterns Workshop",
        "description": dedent("""\
            Hands-on Postman collection for the 'Real-time patterns' workshop.

            Covers all 7 examples (HTTP basics -> polling -> long polling -> webhooks ->
            SSE -> WebSockets -> OpenAI streaming) and both projects (streaming chat,
            webhook dashboard).

            Before you click 'Send' on a request, start the matching server:

                Example 01 - HTTP basics       cd examples/01_http_basics       uvicorn server:app --port 8101
                Example 02 - Short polling     cd examples/02_short_polling     uvicorn server:app --port 8102
                Example 03 - Long polling      cd examples/03_long_polling      uvicorn server:app --port 8103
                Example 04 - Webhooks          cd examples/04_webhooks          uvicorn receiver:app --port 8104
                Example 05 - SSE               cd examples/05_sse               uvicorn server:app --port 8105
                Example 06 - WebSockets        cd examples/06_websockets        uvicorn server:app --port 8106
                Project 1  - Streaming chat    cd projects/project_1_streaming_chat   uvicorn server:app --port 8000
                Project 2  - Webhook dashboard cd projects/project_2_webhook_dashboard uvicorn server:app --port 9000

            Pre-request scripts handle the tricky bits for you:
              - Example 01 'GET /me with JWT' builds a real HS256 JWT for Arjun Kumar.
              - Example 04 webhook requests HMAC-sign the body before sending.
              - Several requests stash returned ids in collection variables so the next
                request can reference them automatically.

            For example 06 (WebSockets) and project 1 WS chat, use Postman's
            New > WebSocket Request feature (HTTP requests can't open WS connections).
            See the example 06 folder description for the URLs.
        """),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "variable": [
        {"key": "base_8101", "value": "http://127.0.0.1:8101", "type": "string"},
        {"key": "base_8102", "value": "http://127.0.0.1:8102", "type": "string"},
        {"key": "base_8103", "value": "http://127.0.0.1:8103", "type": "string"},
        {"key": "base_8104", "value": "http://127.0.0.1:8104", "type": "string"},
        {"key": "base_8105", "value": "http://127.0.0.1:8105", "type": "string"},
        {"key": "base_8106", "value": "http://127.0.0.1:8106", "type": "string"},
        {"key": "base_8000", "value": "http://127.0.0.1:8000", "type": "string"},
        {"key": "base_9000", "value": "http://127.0.0.1:9000", "type": "string"},
        {"key": "jwt_secret", "value": "demo-only-jwt-secret-do-not-use-in-prod-3f8a", "type": "string"},
        {"key": "webhook_secret", "value": "whsec_demo_workshop_secret", "type": "string"},
        {"key": "webhook_secret_p2", "value": "workshop-secret-do-not-use-in-prod", "type": "string"},
        {"key": "arjun_jwt", "value": "", "type": "string"},
        {"key": "tampered_jwt", "value": "", "type": "string"},
        {"key": "event_id", "value": "", "type": "string"},
        {"key": "last_note_id", "value": "1", "type": "string"},
        {"key": "last_order_id", "value": "", "type": "string"},
        {"key": "last_ride_id", "value": "", "type": "string"},
        {"key": "polling_job_id", "value": "", "type": "string"},
    ],
    "item": [
        folder_01, folder_02, folder_03, folder_04,
        folder_05, folder_06,
        folder_p1, folder_p2,
    ],
}


# ---------------------------------------------------------------------------
# Write the JSON
# ---------------------------------------------------------------------------
OUT.write_text(json.dumps(collection, indent=2))

# quick stats
def count_requests(node):
    if "item" not in node:
        return 1
    return sum(count_requests(c) for c in node["item"])

total = sum(count_requests(f) for f in collection["item"])
print(f"wrote {OUT.relative_to(HERE.parent)}")
print(f"  {len(collection['item'])} folders")
print(f"  {total} requests")
print(f"  {len(collection['variable'])} collection variables")
