"""Restaurant recommender agent - real OpenAI streaming over SSE.

This is the "aha" example. What you saw in example 05 (fake SSE token
stream) is exactly what real LLM providers do. Here we hit OpenAI with
stream=True and watch the same wire format with a real model.

We theme it as a "restaurant recommendation agent" for a food delivery
app, so the system prompt and user prompt feel like a realistic feature
you'd build on top of LiveOrder.

Reads OPENAI_API_KEY from ../../.env.

Run AFTER picking up the API key:
    cd examples/07_openai_streaming
    python client.py
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _pretty import (
    banner, demo, divider, pause,
    lesson, note, info, ok, warn, fail, summary_table,
    GREEN, YELLOW, CYAN, MAGENTA, DIM, BOLD, RESET,
)

from dotenv import load_dotenv

# Load .env from the repo root
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

if not os.environ.get("OPENAI_API_KEY"):
    print("ERROR: OPENAI_API_KEY not set in ../../.env")
    sys.exit(1)

from openai import OpenAI

client = OpenAI()


SYSTEM_PROMPT = """\
You are the restaurant recommendation agent for LiveOrder, a food delivery
app in India. You help customers pick dishes based on their cravings,
budget, and dietary preferences. Be concise: name 3 dishes, one line of
description each, and where to typically find them. Keep prices in INR.
Friendly but efficient - the customer is hungry.
"""

USER_PROMPT = (
    "I'm in Bengaluru and want vegetarian Indian dinner under 500 INR. "
    "Something spicy and filling. Suggest 3 dishes."
)


banner(
    "Restaurant recommender agent - REAL OpenAI streaming via SSE",
    "this is the same wire format you saw in example 05, but now with a real LLM",
)


# ---- Step 1: show what we're sending ----------------------------------
demo(1, "What the agent receives")
print(f"  {YELLOW}{BOLD}SYSTEM{RESET}    (the role we've assigned the LLM)")
for line in SYSTEM_PROMPT.strip().splitlines():
    print(f"            {line}")
print()
print(f"  {YELLOW}{BOLD}USER{RESET}      {USER_PROMPT}")

divider()
pause()


# ---- Step 2: stream the response --------------------------------------
demo(2, "Stream the response (each chunk is one SSE event from OpenAI)")
note("watch the words appear one at a time - that's SSE in action")
print()
print(f"  {MAGENTA}{BOLD}AGENT{RESET}     ", end="", flush=True)

t0 = time.time()
first_token_at: float | None = None
chunk_count = 0
total_chars = 0

stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": USER_PROMPT},
    ],
    stream=True,
)

for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        if first_token_at is None:
            first_token_at = time.time() - t0
        chunk_count += 1
        total_chars += len(delta)
        print(f"{GREEN}{delta}{RESET}", end="", flush=True)

print()
total_elapsed = time.time() - t0

divider()
pause()


# ---- Step 3: stream stats ---------------------------------------------
demo(3, "What just happened on the wire")
summary_table([
    ("Model",                      "gpt-4o-mini"),
    ("Chunks received (SSE events)", str(chunk_count)),
    ("Total characters",            str(total_chars)),
    ("Time to first token",         f"{first_token_at*1000:.0f} ms" if first_token_at else "n/a"),
    ("Total stream duration",       f"{total_elapsed:.2f} s"),
    ("Avg ms between chunks",       f"{(total_elapsed/max(chunk_count,1))*1000:.0f} ms"),
])

lesson(
    "Under the hood OpenAI's server sent SSE events that look like: "
    "'data: {\"choices\":[{\"delta\":{\"content\":\"Vada\"}}]}' followed "
    "by a blank line. The openai SDK parsed those for you and exposed "
    "them as chunks. Now you can read the OpenAI API docs and recognise "
    "exactly what stream=True is doing."
)

divider()


# ---- Step 4: same thing with curl, to prove there's no magic ----------
demo(4, "Same thing with raw curl (no SDK)")
print(f"  {DIM}# in your terminal:{RESET}")
print()
print(f"  {CYAN}OPENAI_API_KEY=$(grep ^OPENAI_API_KEY ../../.env | cut -d= -f2-){RESET}")
print()
print(f"  {CYAN}curl -N https://api.openai.com/v1/chat/completions \\{RESET}")
print(f"  {CYAN}  -H \"Authorization: Bearer $OPENAI_API_KEY\" \\{RESET}")
print(f"  {CYAN}  -H \"content-type: application/json\" \\{RESET}")
print(f"  {CYAN}  -d '{{\"model\":\"gpt-4o-mini\",\"stream\":true,\"messages\":[{{\"role\":\"user\",\"content\":\"count to 5\"}}]}}'{RESET}")
print()
print(f"  You'll see raw 'data: {{\"choices\":[{{\"delta\":{{\"content\":\"One\"}}}}]}}'")
print(f"  lines streaming in. Then 'data: [DONE]'. That's the entire protocol.")
print()
print(f"  Every LLM provider on the planet does this. Now you know how.")
print()
