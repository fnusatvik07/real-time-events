"""SSE client - watches a chat response stream in token by token.

The point of this demo is to make the SSE wire format concrete: each
event arrives with a small delay, the client reads it as it comes, and
the cumulative response appears word-by-word like in ChatGPT.

Run AFTER starting the server in another terminal:
    Terminal 1:  uvicorn server:app --port 8105
    Terminal 2:  python client.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _pretty import (
    banner, demo, divider,
    request_line, request_body, response_line,
    lesson, note, info, ok, summary_table, preflight_check,
    GREEN, CYAN, YELLOW, MAGENTA, DIM, BOLD, RESET,
)

import httpx

URL = "http://127.0.0.1:8105/chat"
preflight_check("http://127.0.0.1:8105", expected_keyword="SSE chat streaming")


banner(
    "SSE - a ChatGPT-style streaming chat response",
    "the server holds ONE HTTP connection open and pushes tokens down it",
)


# ---- Step 1: send the prompt ------------------------------------------
demo(1, "Send a prompt; the server will stream a response token-by-token")

prompt = {"prompt": "What are 3 must-try Mumbai street foods?"}
request_line("POST", URL)
request_body(prompt)


# ---- Step 2: read the SSE stream raw ----------------------------------
print()
demo(2, "Watch the raw SSE wire format - each event is 3 lines + a blank line")
note("the first 5 raw events are shown verbatim so you see the protocol")
print()

# Parse SSE events as they arrive.
# An SSE event is a block of lines (event:, data:, id:) followed by a
# blank line. We'll collect lines, and when we see a blank line, dispatch.

token_count = 0
shown_raw = 0
t0 = time.time()
first_token_at: float | None = None

assembled_response: list[str] = []

with httpx.stream("POST", URL, json=prompt, timeout=30) as r:
    response_line(r.status_code, r.reason_phrase,
                  r.headers.get("content-type", "?").split(";")[0])
    print(f"            {DIM}(connection stays open; events arrive over time){RESET}")
    print()

    cur_event: dict = {}

    for raw_line in r.iter_lines():
        if shown_raw < 30:   # show the first few events verbatim
            print(f"  {DIM}{repr(raw_line)}{RESET}")
            shown_raw += 1
            if shown_raw == 30:
                print(f"  {DIM}... (the rest will be parsed and shown as words below){RESET}")
                print()

        if raw_line == "":
            # end of event - dispatch
            if cur_event.get("event") == "token":
                if first_token_at is None:
                    first_token_at = time.time() - t0
                token_count += 1
                payload = json.loads(cur_event["data"])
                assembled_response.append(payload["text"])
            elif cur_event.get("event") == "done":
                pass
            cur_event = {}
            continue

        if raw_line.startswith("event:"):
            cur_event["event"] = raw_line[6:].strip()
        elif raw_line.startswith("data:"):
            cur_event["data"] = raw_line[5:].strip()
        elif raw_line.startswith("id:"):
            cur_event["id"] = raw_line[3:].strip()

total_elapsed = time.time() - t0

divider()


# ---- Step 3: show the assembled response ------------------------------
demo(3, "Assembled response (built up word by word from the events)")
print()
text = "".join(assembled_response)
# Wrap nicely
import textwrap
for line in textwrap.wrap(text, width=72):
    print(f"  {GREEN}{line}{RESET}")
print()


# ---- Step 4: stats ----------------------------------------------------
divider()
demo(4, "Stream stats")
summary_table([
    ("Total tokens received",      str(token_count)),
    ("Time to first token",        f"{first_token_at*1000:.0f} ms" if first_token_at else "n/a"),
    ("Total stream time",          f"{total_elapsed:.2f} s"),
    ("Average gap between tokens", f"{(total_elapsed / max(token_count, 1))*1000:.0f} ms"),
    ("HTTP requests made",         "1   (one connection, many events down it)"),
])

lesson(
    "What you just saw IS Server-Sent Events. One HTTP request. Many "
    "events pushed down the same response body, separated by blank lines. "
    "This is EXACTLY the wire format OpenAI returns when you set "
    "stream=True. Run example 07 next to see the real OpenAI API doing "
    "the same thing."
)

print()
print(f"  In a browser, the client side is two lines:")
print(f"    {CYAN}const es = new EventSource('/chat');{RESET}")
print(f"    {CYAN}es.addEventListener('token', e => append(JSON.parse(e.data).text));{RESET}")
print()
print(f"  The browser handles auto-reconnect, Last-Event-ID resume, and ")
print(f"  parsing for you. Nothing else to install.")
print()
