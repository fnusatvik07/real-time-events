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
assert_contains "client received hit_number"          "$OUT" "hit_number"
assert_contains "client received echo uppercase"      "$OUT" "REAL-TIME WORKSHOP"
assert_contains "client printed 3 sample requests"    "$OUT" "Request 1" "Request 2" "Request 3"
stop_all_servers

# ============================================================
# Example 02 - Short polling
# ============================================================
hdr "02_short_polling  (port 8102)"
if start_server "$HERE/02_short_polling" "server" 8102 "$LOGS/02.log"; then
    ok "server came up on :8102"
else
    fail "server did not start"
fi
VAL=$(curl -s http://127.0.0.1:8102/value)
assert_contains "/value endpoint returns counter"     "$VAL" '"counter":'
stop_all_servers

# ============================================================
# Example 03 - Long polling
# ============================================================
hdr "03_long_polling  (port 8103)"
if start_server "$HERE/03_long_polling" "server" 8103 "$LOGS/03.log"; then
    ok "server came up on :8103"
else
    fail "server did not start"
fi
# Long poll with since=999 (counter is 0) and short timeout -> should time out
TIMING=$($PYTHON - <<'PY'
import time, httpx
t0 = time.time()
r = httpx.get("http://127.0.0.1:8103/wait?since=999&timeout=1", timeout=5)
print(f"{round((time.time()-t0)*1000)}||{r.text}")
PY
)
ELAPSED="${TIMING%%||*}"
BODY="${TIMING##*||}"
assert_contains "long-poll times out cleanly (${ELAPSED}ms)" "$BODY" '"timed_out":true'

# Long poll with since=-1 -> server has counter=0 > -1, returns immediately
RESP=$(curl -s "http://127.0.0.1:8103/wait?since=-1&timeout=5")
assert_contains "long-poll returns immediately when data available" "$RESP" '"timed_out":false'
stop_all_servers

# ============================================================
# Example 04 - Webhooks
# ============================================================
hdr "04_webhooks  (port 8104)"
if start_server "$HERE/04_webhooks" "receiver" 8104 "$LOGS/04.log"; then
    ok "receiver came up on :8104"
else
    fail "receiver did not start"
fi
OUT=$(cd "$HERE/04_webhooks" && $PYTHON sender.py 2>&1)
# We assert by extracting per-case lines using grep -A2
CASE1=$(grep -A2 "Case 1" <<<"$OUT")
CASE2=$(grep -A2 "Case 2" <<<"$OUT")
CASE3=$(grep -A2 "Case 3" <<<"$OUT")
assert_contains "case 1 (signed event) accepted"   "$CASE1" "HTTP 200" "'duplicate': False"
assert_contains "case 2 (replay) deduped"          "$CASE2" "HTTP 200" "'duplicate': True"
assert_contains "case 3 (unsigned) rejected"       "$CASE3" "HTTP 401"
stop_all_servers

# ============================================================
# Example 05 - SSE
# ============================================================
hdr "05_sse  (port 8105)"
if start_server "$HERE/05_sse" "server" 8105 "$LOGS/05.log"; then
    ok "server came up on :8105"
else
    fail "server did not start"
fi
OUT=$(cd "$HERE/05_sse" && $PYTHON client.py 2>&1)
TOKEN_COUNT=$(grep -c "data: token-" <<<"$OUT")
if [ "$TOKEN_COUNT" = "10" ]; then ok "received 10 token events"; else fail "expected 10 token events, got $TOKEN_COUNT"; fi
assert_contains "received done event"          "$OUT" "event: done"
assert_contains "stream closed cleanly"        "$OUT" "stream closed"
stop_all_servers

# ============================================================
# Example 06 - WebSockets
# ============================================================
hdr "06_websockets  (port 8106)"
if start_server "$HERE/06_websockets" "server" 8106 "$LOGS/06.log"; then
    ok "server came up on :8106"
else
    fail "server did not start"
fi
OUT=$(cd "$HERE/06_websockets" && $PYTHON client.py 2>&1)
SEND_COUNT=$(grep -c "SEND:" <<<"$OUT")
RECV_COUNT=$(grep -c "RECV:" <<<"$OUT")
if [ "$SEND_COUNT" = "3" ]; then ok "client sent 3 messages"; else fail "client sent $SEND_COUNT messages (expected 3)"; fi
if [ "$RECV_COUNT" -ge 3 ]; then ok "client received >= 3 broadcasts (got $RECV_COUNT)"; else fail "client received only $RECV_COUNT broadcasts"; fi
stop_all_servers

# ============================================================
# Example 07 - OpenAI streaming
# ============================================================
hdr "07_openai_streaming  (no server; talks to api.openai.com)"
if [ -f "$ROOT/.env" ] && grep -q "^OPENAI_API_KEY=sk-" "$ROOT/.env"; then
    ok "OPENAI_API_KEY found in .env"
    OUT=$(cd "$HERE/07_openai_streaming" && $PYTHON client.py 2>&1)
    if grep -qi "one" <<<"$OUT" && grep -qi "ten" <<<"$OUT"; then
        ok "LLM streamed words 'one' through 'ten'"
    else
        fail "LLM stream output unexpected (got: $(head -5 <<<"$OUT"))"
    fi
    assert_contains "metrics reported (first token, chunks)" "$OUT" "first token:" "chunks"
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
