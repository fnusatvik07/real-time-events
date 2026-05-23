"""SSE server - relays a REAL OpenAI stream to the client.

This is the pattern most modern AI apps use: the browser opens an SSE
connection to YOUR backend, your backend calls OpenAI (or Anthropic) with
stream=True, and your backend re-emits each chunk as an SSE event to the
browser. From the browser's perspective it's just an SSE stream from your
own domain.

Why proxy instead of letting the browser call OpenAI directly?
  1. Your API key never reaches the browser.
  2. You can transform / filter / log the stream.
  3. You can add auth, rate limiting, prompt templating.
  4. CORS and DNS get simpler when everything looks like your own domain.

Reads OPENAI_API_KEY from ../../.env.

Run:
    uvicorn server:app --port 8105
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

from openai import AsyncOpenAI

app = FastAPI(title="SSE chat streaming demo")

# One async OpenAI client, reused across requests.
client = AsyncOpenAI()
MODEL = "gpt-4o-mini"

# Friendly system prompt so the LLM stays on theme.
SYSTEM_PROMPT = (
    "You are a friendly food expert for an Indian food delivery app called "
    "LiveOrder. Keep answers short (5-8 short sentences), concrete, and "
    "tasty. No markdown headers, just plain paragraphs."
)

DEFAULT_PROMPT = "What are 3 must-try Mumbai street foods? One short paragraph per dish."


class ChatRequest(BaseModel):
    prompt: str = DEFAULT_PROMPT


@app.get("/")
def root():
    return {
        "service": "SSE chat streaming demo",
        "model":   MODEL,
        "openai_key_configured": bool(os.environ.get("OPENAI_API_KEY")),
        "endpoints": {
            "POST /chat":
                "stream a real OpenAI response over SSE.  Body: {\"prompt\": \"...\"}",
        },
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    """Relays a real OpenAI streaming response to the client as SSE events."""

    async def gen():
        # opening event so the client knows the stream is alive
        yield f"event: open\ndata: {json.dumps({'prompt': req.prompt, 'model': MODEL})}\n\n"

        try:
            stream = await client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": req.prompt},
                ],
                stream=True,
            )

            i = 0
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if not delta:
                    continue
                payload = {"text": delta, "index": i}
                # Each event: id (resume support) + event type + JSON payload + blank line.
                yield f"id: {i}\nevent: token\ndata: {json.dumps(payload)}\n\n"
                i += 1

            yield f"event: done\ndata: {json.dumps({'token_count': i})}\n\n"

        except asyncio.CancelledError:
            # Client disconnected mid-stream. Let the cancellation propagate.
            raise
        except Exception as e:
            # Send a friendly error event instead of dying silently.
            err = {"error": type(e).__name__, "message": str(e)}
            yield f"event: error\ndata: {json.dumps(err)}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":      "no-cache, no-transform",
            "X-Accel-Buffering":  "no",   # tell nginx-style proxies not to buffer
        },
    )
