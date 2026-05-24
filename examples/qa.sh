#!/usr/bin/env bash
# Automated QA - runs every example end-to-end, asserts expected behavior.
# Also smoke-tests the two projects.
#
# Run from the examples/ directory:
#   bash qa.sh

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
LOGS="$HERE/.qa_logs"
mkdir -p "$LOGS"

PYTHON="${PYTHON:-python}"
# Skip interactive pauses when clients are run from qa.sh
export NO_PAUSE=1

# colors
G='\033[0;32m'; R='\033[0;31m'; B='\033[0;34m'; N='\033[0m'

PASSED=0
FAILED=0
FAILS=()

ok()   { echo -e "  ${G}OK${N}    $1"; PASSED=$((PASSED+1)); }
fail() { echo -e "  ${R}FAIL${N}  $1"; FAILED=$((FAILED+1)); FAILS+=("$1"); }
hdr()  { echo; echo -e "${B}== $1 ==${N}"; }

# assert_contains LABEL HAYSTACK NEEDLE [NEEDLE2 ...]
# Passes if ALL needles are substrings of haystack.
assert_contains() {
    local label="$1"; shift
    local hay="$1"; shift
    for needle in "$@"; do
        if ! grep -qF -- "$needle" <<<"$hay"; then
            fail "$label  (missing: $needle)"
            return 1
        fi
    done
    ok "$label"
}

# assert_status LABEL EXPECTED_STATUS URL
assert_status() {
    local label="$1" expected="$2" url="$3"
    local actual
    actual=$(curl -s -o /dev/null -w "%{http_code}" "$url")
    if [ "$actual" = "$expected" ]; then ok "$label ($actual)"; else fail "$label (got $actual, expected $expected)"; fi
}

# wait_for_port PORT - block until something is listening (up to 10s)
wait_for_port() {
    local port=$1
    for _ in $(seq 1 50); do
        if curl -s -o /dev/null --max-time 0.5 "http://127.0.0.1:$port/" 2>/dev/null; then
            return 0
        fi
        sleep 0.2
    done
    return 1
}

start_server() {
    local cwd=$1 module=$2 port=$3 logfile=$4
    # Disown so bash job-control "Terminated" messages stay quiet at pkill time.
    (
        cd "$cwd"
        $PYTHON -m uvicorn "${module}:app" --host 127.0.0.1 --port "$port" --log-level warning >"$logfile" 2>&1 &
        disown
    )
    sleep 0.4
    wait_for_port "$port"
}

stop_all_servers() {
    {
        pkill -f "uvicorn .*--port 810[1-6]"
        pkill -f "uvicorn .*--port 8000"
        pkill -f "uvicorn .*--port 9000"
    } 2>/dev/null
    sleep 0.7
}

trap stop_all_servers EXIT
stop_all_servers   # initial cleanup

# ============================================================
# Example 01 - HTTP basics
# ============================================================
hdr "01_http_basics  (port 8101)"
if start_server "$HERE/01_http_basics" "server" 8101 "$LOGS/01.log"; then
    ok "server came up on :8101"
else
    fail "server did not start (see $LOGS/01.log)"
fi
OUT=$(cd "$HERE/01_http_basics" && $PYTHON client.py 2>&1)
assert_contains "all 7 demos ran"             "$OUT" "Step 1" "Step 2" "Step 3" "Step 4" "Step 5" "Step 6" "Step 7"
assert_contains "shared counter increments"   "$OUT" '"counter": 1' '"counter": 2' '"counter": 3'
assert_contains "JWT auth: valid token decoded by server" "$OUT" '"name": "Arjun Kumar"' '"user_id": "usr_arjun_8c3d2"'
assert_contains "JWT auth: 3 sub-demos shown" "$OUT" "call A" "call B" "call C"
assert_contains "JWT auth: tampered token rejected" "$OUT" "JWT verification failed"
assert_contains "POST returns 201 + GET 404"  "$OUT" "201 Created" "404"
assert_contains "lessons printed"             "$OUT" "LESSON"
stop_all_servers

# ============================================================
# Example 02 - Short polling (Swiggy order tracker)
# ============================================================
hdr "02_short_polling  (port 8102 - Swiggy order tracker)"
if start_server "$HERE/02_short_polling" "server" 8102 "$LOGS/02.log"; then
    ok "server came up on :8102"
else
    fail "server did not start"
fi
# Server should return list of stages and an info page
ROOT_RESP=$(curl -s http://127.0.0.1:8102/)
assert_contains "info page lists order stages" "$ROOT_RESP" "placed" "delivered" "restaurant_confirmed"
# Create an order and verify shape
ORDER_RESP=$(curl -s -X POST http://127.0.0.1:8102/orders \
    -H "content-type: application/json" \
    -d '{"customer":"Raj","item":"Biryani","amount_inr":450}')
assert_contains "POST /orders returns id+status"  "$ORDER_RESP" '"id"' '"status":"placed"' '"customer":"Raj"'
# (We don't run the full client here because it takes ~40s. Smoke-test only.)
stop_all_servers

# ============================================================
# Example 03 - Long polling (Uber ride dispatch)
# ============================================================
hdr "03_long_polling  (port 8103 - Uber ride dispatch)"
if start_server "$HERE/03_long_polling" "server" 8103 "$LOGS/03.log"; then
    ok "server came up on :8103"
else
    fail "server did not start"
fi
# Create a ride
RIDE=$(curl -s -X POST http://127.0.0.1:8103/rides \
    -H "content-type: application/json" \
    -d '{"rider":"Raj","pickup":"Indiranagar","dropoff":"Airport"}')
assert_contains "POST /rides returns id and status" "$RIDE" '"id":"ride_' '"status":"searching"'
RIDE_ID=$($PYTHON -c "import sys,json; print(json.loads(sys.argv[1])['id'])" "$RIDE")
# Long-poll with short timeout; should return either timed_out:true or the accepted ride
WAIT_RESP=$(curl -s "http://127.0.0.1:8103/rides/$RIDE_ID/wait?timeout=15")
if grep -q '"status":"accepted"' <<<"$WAIT_RESP"; then
    assert_contains "long-poll resolved with driver" "$WAIT_RESP" '"driver"' '"status":"accepted"'
elif grep -q '"timed_out":true' <<<"$WAIT_RESP"; then
    ok "long-poll returned timed_out (driver took longer than 15s)"
else
    fail "long-poll returned unexpected: $WAIT_RESP"
fi
stop_all_servers

# ============================================================
# Example 04 - Webhooks (Stripe payment for biryani)
# ============================================================
hdr "04_webhooks  (port 8104 - Stripe payment receiver)"
if start_server "$HERE/04_webhooks" "receiver" 8104 "$LOGS/04.log"; then
    ok "receiver came up on :8104"
else
    fail "receiver did not start"
fi
OUT=$(cd "$HERE/04_webhooks" && $PYTHON sender.py 2>&1)
assert_contains "all 4 webhook cases ran"    "$OUT" "Case 1:" "Case 2:" "Case 3:" "Case 4:"
assert_contains "case 1 accepted (200)"      "$OUT" '"duplicate": false' "payment_intent.succeeded"
assert_contains "case 2 deduped (duplicate)" "$OUT" '"duplicate": true'
assert_contains "case 3 refund processed"    "$OUT" "charge.refunded"
assert_contains "case 4 forged event rejected (401)" "$OUT" "401" "invalid signature"
# Check receiver logs printed the worker actions
RECEIVER_LOG=$(cat "$LOGS/04.log")
assert_contains "receiver logged worker actions" "$RECEIVER_LOG" "ACCEPTED" "would: marked order"
stop_all_servers

# ============================================================
# Example 05 - SSE (Mumbai street food chat)
# ============================================================
hdr "05_sse  (port 8105 - chat streaming)"
if start_server "$HERE/05_sse" "server" 8105 "$LOGS/05.log"; then
    ok "server came up on :8105"
else
    fail "server did not start"
fi
OUT=$(cd "$HERE/05_sse" && $PYTHON client.py 2>&1)
TOKEN_EVENTS=$(grep -c "'event: token'" <<<"$OUT")
if [ "$TOKEN_EVENTS" -ge 5 ]; then
    ok "received raw token events ($TOKEN_EVENTS shown)"
else
    fail "expected >=5 raw token events shown, got $TOKEN_EVENTS"
fi
# LLM responses vary, so we don't assert on specific dish names. We check
# that the prompt was echoed in event: open, that tokens flowed, that the
# stream completed cleanly, and that the assembled-response section ran.
assert_contains "prompt echoed in event:open" "$OUT" "Mumbai street foods"
assert_contains "stream completed cleanly"    "$OUT" "Assembled response"
assert_contains "stream stats printed"        "$OUT" "Total tokens received" "Time to first token"
stop_all_servers

# ============================================================
# Example 06 - WebSockets (delivery chat)
# ============================================================
hdr "06_websockets  (port 8106 - driver/customer chat)"
if start_server "$HERE/06_websockets" "server" 8106 "$LOGS/06.log"; then
    ok "server came up on :8106"
else
    fail "server did not start"
fi
# Start a driver in the background, then run the customer in the foreground.
# They join the same order; the driver script and customer script send messages
# that each one will see arrive on the other.
(cd "$HERE/06_websockets" && $PYTHON client.py --role driver --order qa_room --script 2>&1 > "$LOGS/06_driver.log") &
DRIVER_PID=$!
sleep 0.5
OUT=$(cd "$HERE/06_websockets" && $PYTHON client.py --role customer --order qa_room --script 2>&1)
wait $DRIVER_PID 2>/dev/null
# Customer should have SENT its own messages AND received the driver's messages
assert_contains "customer connected"                "$OUT" "connected as customer"
assert_contains "customer sent its scripted lines"  "$OUT" "buzzer is broken" "blue shirt"
assert_contains "customer received driver messages" "$OUT" "Hi Raj" "6 minutes away" "Looking for blue shirt"
stop_all_servers

# ============================================================
# Example 07 - OpenAI streaming (restaurant recommender agent)
# ============================================================
hdr "07_openai_streaming  (no server; talks to api.openai.com)"
if [ -f "$ROOT/.env" ] && grep -q "^OPENAI_API_KEY=sk-" "$ROOT/.env"; then
    ok "OPENAI_API_KEY found in .env"
    OUT=$(cd "$HERE/07_openai_streaming" && $PYTHON client.py 2>&1)
    assert_contains "agent persona shown"       "$OUT" "SYSTEM" "restaurant recommendation agent"
    assert_contains "agent streamed a response" "$OUT" "AGENT"
    assert_contains "stream stats printed"      "$OUT" "Time to first token" "Total stream duration"
else
    fail "OPENAI_API_KEY missing or malformed in .env"
fi

# ============================================================
# Project 1 - Streaming chat (uses OpenAI)
# ============================================================
hdr "Project 1 - streaming chat  (port 8000)"
if start_server "$ROOT/projects/project_1_streaming_chat" "server" 8000 "$LOGS/p1.log"; then
    ok "project 1 server came up on :8000"
else
    fail "project 1 server did not start (see $LOGS/p1.log)"
fi
assert_status "index page" 200 "http://127.0.0.1:8000/"
ABOUT=$(curl -s http://127.0.0.1:8000/api/about)
assert_contains "/api/about lists all 3 patterns" "$ABOUT" "polling" "sse" "ws"

# Polling chain
JOB=$(curl -s -X POST http://127.0.0.1:8000/api/polling/start \
        -H "content-type: application/json" \
        -d '{"prompt":"reply with exactly: ok"}' | $PYTHON -c "import sys,json; print(json.load(sys.stdin).get('job_id',''))")
if [ -n "$JOB" ]; then ok "polling start returned job_id"; else fail "polling start broken"; fi

# Poll until done (up to 30s)
DONE=""
for _ in $(seq 1 15); do
    sleep 2
    STATUS=$(curl -s "http://127.0.0.1:8000/api/polling/status/$JOB")
    if grep -q '"status":"done"' <<<"$STATUS"; then DONE=1; break; fi
done
if [ "$DONE" = "1" ]; then ok "polling job completed"; else fail "polling job did not complete in 30s (last: $STATUS)"; fi

RESULT=$(curl -s "http://127.0.0.1:8000/api/polling/result/$JOB")
assert_contains "polling result fetched" "$RESULT" '"result"'

# SSE
SSE_OUT=$(curl -s -N -X POST http://127.0.0.1:8000/api/sse/chat \
    -H "content-type: application/json" -d '{"prompt":"count 1 2 3"}' --max-time 20 | head -50)
assert_contains "SSE chat streamed token events" "$SSE_OUT" "event: token"

# WebSocket
WS_OUT=$($PYTHON - <<'PY'
import asyncio, websockets, json
async def go():
    async with websockets.connect('ws://127.0.0.1:8000/api/ws/chat') as ws:
        await ws.send(json.dumps({'type':'prompt','text':'say ok'}))
        tokens = 0
        async for raw in ws:
            m = json.loads(raw)
            if m['type'] == 'token': tokens += 1
            elif m['type'] == 'done':
                print(f'tokens={tokens}'); return
            elif m['type'] == 'error':
                print(f'error: {m["message"]}'); return
asyncio.run(go())
PY
2>&1)
if grep -q "^tokens=" <<<"$WS_OUT"; then ok "WS chat streamed tokens ($WS_OUT)"; else fail "WS chat broken: $WS_OUT"; fi
stop_all_servers

# ============================================================
# Project 2 - Webhook dashboard
# ============================================================
hdr "Project 2 - webhook dashboard  (port 9000)"
rm -f "$ROOT/projects/project_2_webhook_dashboard/events.db"
if start_server "$ROOT/projects/project_2_webhook_dashboard" "server" 9000 "$LOGS/p2.log"; then
    ok "project 2 server came up on :9000"
else
    fail "project 2 server did not start"
fi
assert_status "dashboard page" 200 "http://127.0.0.1:9000/"

curl -s -X POST http://127.0.0.1:9000/admin/reset >/dev/null

BURST=$(curl -s -X POST "http://127.0.0.1:9000/simulate/burst?n=3")
assert_contains "burst stored 3 events" "$BURST" '"fired":3'

EVENTS=$(curl -s "http://127.0.0.1:9000/events?since=0")
COUNT=$($PYTHON -c "import sys,json; print(len(json.load(sys.stdin)['events']))" <<<"$EVENTS")
if [ "$COUNT" = "3" ]; then ok "polling endpoint returns 3 events"; else fail "polling endpoint returned $COUNT events"; fi

REPLAY=$(curl -s -X POST http://127.0.0.1:9000/simulate/replay)
assert_contains "dedup works on replay" "$REPLAY" '"duplicate":true'

FORGE=$(curl -s -X POST http://127.0.0.1:9000/simulate/forgery)
assert_contains "forgery rejected with 401" "$FORGE" '"status":401'

# SSE live push: subscribe, fire events, confirm they arrive
(curl -s -N "http://127.0.0.1:9000/stream?since=999" --max-time 5 > "$LOGS/p2_sse.out") &
SSE_PID=$!
sleep 1
curl -s -X POST "http://127.0.0.1:9000/simulate/burst?n=2" >/dev/null
sleep 4
wait $SSE_PID 2>/dev/null
if grep -q "event: payment" "$LOGS/p2_sse.out"; then ok "SSE pushed live events to subscribers"; else fail "SSE live push did not deliver"; fi
stop_all_servers

# ============================================================
# Project 3 - LiveOrder (all 4 patterns in one app)
# ============================================================
hdr "Project 3 - LiveOrder  (port 7000 - all 4 patterns in one app)"
if start_server "$ROOT/projects/project_3_liveorder" "server" 7000 "$LOGS/p3.log"; then
    ok "project 3 server came up on :7000"
else
    fail "project 3 server did not start (see $LOGS/p3.log)"
fi
assert_status "index page" 200 "http://127.0.0.1:7000/"
ABOUT3=$(curl -s http://127.0.0.1:7000/api/about)
assert_contains "/api/about lists all patterns" "$ABOUT3" "webhook" "sse" "websocket" "polling"

# Place an order
ORDER=$(curl -s -X POST http://127.0.0.1:7000/api/orders \
    -H "content-type: application/json" \
    -d '{"customer":"Raj","item":"Biryani","amount_inr":450}')
ORDER_ID=$($PYTHON -c "import sys,json; print(json.load(sys.stdin)['id'])" <<<"$ORDER")
assert_contains "POST /api/orders returns id + awaiting_payment" "$ORDER" '"id":"ord_' '"status":"awaiting_payment"'

# Simulate the Stripe payment webhook
SIM=$(curl -s -X POST "http://127.0.0.1:7000/api/simulate/payment/$ORDER_ID")
assert_contains "webhook simulator round-trip 200" "$SIM" '"received_by_webhook":200' '"sent":true'

# Order should now be paid (state machine fired immediately on the webhook)
sleep 0.5
SNAP=$(curl -s "http://127.0.0.1:7000/api/orders/$ORDER_ID")
assert_contains "webhook transitioned the order to 'paid'" "$SNAP" '"status":"paid"'

# Kick a revenue report and confirm we can poll it
KICK=$(curl -s -X POST http://127.0.0.1:7000/api/reports/revenue)
REPORT_ID=$($PYTHON -c "import sys,json; print(json.load(sys.stdin)['id'])" <<<"$KICK")
assert_contains "report kicked off (pending)" "$KICK" '"status":"pending"' '"id":"rep_'
sleep 0.3
POLL1=$(curl -s "http://127.0.0.1:7000/api/reports/$REPORT_ID")
assert_contains "report status pollable" "$POLL1" '"status":' '"elapsed_ms":'

# AI recommender SSE (smoke check)
RECCO=$(curl -s -N -X POST http://127.0.0.1:7000/api/recommend \
    -H "content-type: application/json" \
    -d '{"prompt":"name one Indian dessert in two words"}' --max-time 12 | head -10)
assert_contains "/api/recommend streams real LLM tokens" "$RECCO" "event: token"

# WebSocket chat smoke test
WS3_OUT=$($PYTHON - <<PY
import asyncio, websockets, json
async def go():
    async with websockets.connect('ws://127.0.0.1:7000/api/chat/$ORDER_ID?role=customer') as ws:
        # first message from server should be the system "connected as" hello
        raw = await asyncio.wait_for(ws.recv(), timeout=5)
        m = json.loads(raw)
        print('system:', m.get('type'), m.get('text', '')[:40])
        await ws.send(json.dumps({'type': 'msg', 'text': 'hi from qa'}))
        # echo of our own broadcast
        raw = await asyncio.wait_for(ws.recv(), timeout=5)
        m = json.loads(raw)
        print('echo:', m.get('type'), m.get('text', ''))
asyncio.run(go())
PY
2>&1)
assert_contains "chat WS accepts + echoes" "$WS3_OUT" "system:" "echo: msg hi from qa"
stop_all_servers

# ============================================================
# Summary
# ============================================================
echo
echo "============================================================"
TOTAL=$((PASSED + FAILED))
if [ $FAILED -eq 0 ]; then
    echo -e "${G}ALL $TOTAL CHECKS PASSED${N}"
    exit 0
else
    echo -e "${R}FAILED: $FAILED / $TOTAL${N}"
    for f in "${FAILS[@]}"; do echo "  - $f"; done
    exit 1
fi
