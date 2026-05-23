"""SSE server - mimic a ChatGPT-style streaming chat response.

POST /chat with a {"prompt": "..."} body returns a text/event-stream where
the server streams a (canned) LLM response word-by-word with a small delay,
exactly the way OpenAI / Anthropic stream tokens in production.

We use a canned response so the demo is deterministic. Example 07 swaps in
a REAL OpenAI call to show the same wire format with a real model.

Run:
    uvicorn server:app --port 8105
"""
from __future__ import annotations

import asyncio
import json
import time

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="SSE chat streaming demo")


# A canned multi-paragraph response. Split into words so each word is one
# SSE event - same shape as a real LLM streaming tokens.
CANNED_RESPONSE = (
    "Great question! Here are 3 must-try Mumbai street foods you can't miss. "
    "First, Vada Pav - the iconic Mumbai burger: a spiced potato fritter inside "
    "a soft pav bun, served with green chutney and a fried chili. "
    "Second, Pav Bhaji - a buttery mash of vegetables, spices, and tomatoes, "
    "scooped up with toasted pav. Best eaten at Juhu Beach in the evening. "
    "Third, Bombay Sandwich - a triple-decker with potato, beetroot, cucumber, "
    "tomato, and green chutney, grilled until crisp. Enjoy!"
)


class ChatRequest(BaseModel):
    prompt: str = "What are 3 must-try Mumbai street foods?"


@app.get("/")
def root():
    return {
        "service": "SSE chat streaming demo",
        "endpoints": {
            "POST /chat": "stream a fake LLM response token-by-token (SSE)",
        },
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    """Streams the canned response as SSE events, one word per event."""

    async def gen():
        # opening event so the client knows the stream started
        yield f"event: open\ndata: {json.dumps({'prompt': req.prompt})}\n\n"

        words = CANNED_RESPONSE.split()
        for i, word in enumerate(words):
            payload = {"text": word + " ", "index": i}
            # Each event has an id (resume-friendly), an event type (lets
            # clients subscribe with addEventListener), and a JSON payload.
            yield f"id: {i}\nevent: token\ndata: {json.dumps(payload)}\n\n"
            await asyncio.sleep(0.08)   # 80ms per token feels like a real LLM

        # final event so the client knows we're done
        yield f"event: done\ndata: {json.dumps({'token_count': len(words)})}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",   # tell nginx-style proxies not to buffer
        },
    )
