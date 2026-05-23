"""Real-world example - OpenAI streaming uses SSE under the hood.

Run this AFTER understanding example 05 (SSE). It shows how the patterns
you just learned power every modern LLM chat UI.

Reads OPENAI_API_KEY from ../../.env.
"""
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Load .env from the repo root
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

if not os.environ.get("OPENAI_API_KEY"):
    raise SystemExit("OPENAI_API_KEY not set in .env")

client = OpenAI()

print("Asking the LLM to count from one to ten.\n")
print("Streamed response (each chunk is one SSE event):\n")

t0 = time.time()
first_token_at = None
chunk_count = 0

stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Count from one to ten in words, one per line. No commentary."}],
    stream=True,
)

for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        if first_token_at is None:
            first_token_at = time.time() - t0
        chunk_count += 1
        print(delta, end="", flush=True)

total = time.time() - t0
print()
print()
print(f"first token: {first_token_at*1000:.0f}ms")
print(f"total      : {total*1000:.0f}ms")
print(f"chunks     : {chunk_count}")
print()
print("Under the hood OpenAI's server sent SSE events like:")
print("  data: {\"choices\":[{\"delta\":{\"content\":\"One\"}}]}")
print("  data: {\"choices\":[{\"delta\":{\"content\":\"\\n\"}}]}")
print("  data: {\"choices\":[{\"delta\":{\"content\":\"Two\"}}]}")
print("  ...")
print("  data: [DONE]")
print()
print("The openai SDK parses those for you. You now know what's happening.")
