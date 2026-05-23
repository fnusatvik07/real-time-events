"""Project 1: Streaming AI Chat - three implementations, one app.

This single FastAPI app exposes the same "ask an LLM" feature through three
different real-time patterns, so students can see the exact same backend logic
delivered to the browser three different ways and feel the UX difference.

Run:
    uvicorn server:app --reload --port 8000
Open:
    http://localhost:8000/

Endpoints:
    GET  /                              -> the side-by-side UI
    GET  /static/*                      -> static assets

    [Polling implementation]
    POST /api/polling/start             -> create a job, return job_id
    GET  /api/polling/status/{job_id}   -> poll until status == done
    GET  /api/polling/result/{job_id}   -> fetch the final completed text

    [SSE implementation]
    POST /api/sse/chat                  -> stream tokens as SSE events

    [WebSocket implementation]
    WS   /api/ws/chat                   -> bidirectional: send prompt, stream tokens,
                                           support interruption mid-stream
"""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI

# Load OPENAI_API_KEY from ../../.env
load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

ROOT = Path(__file__).parent
STATIC = ROOT / "static"

client = AsyncOpenAI()  # uses OPENAI_API_KEY
MODEL = "gpt-4o-mini"


# ---------------------------------------------------------------------------
# Shared in-memory job store (Polling implementation)
# ---------------------------------------------------------------------------
class Job:
    def __init__(self, prompt: str):
        self.id = str(uuid.uuid4())
        self.prompt = prompt
        self.status: str = "pending"        # pending → running → done | error
        self.result: str = ""
        self.error: str | None = None
        self.started_at: float = time.time()
        self.finished_at: float | None = None


JOBS: Dict[str, Job] = {}


async def _run_job(job: Job):
    """Background worker that calls OpenAI and stores the full result."""
    job.status = "running"
    try:
        resp = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": job.prompt}],
        )
        job.result = resp.choices[0].message.content or ""
        job.status = "done"
    except Exception as exc:
        job.error = str(exc)
        job.status = "error"
    finally:
        job.finished_at = time.time()


# ---------------------------------------------------------------------------
# App + lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.environ.get("OPENAI_API_KEY"):
        print("[warn] OPENAI_API_KEY not set; LLM calls will fail")
    yield


app = FastAPI(title="Streaming AI Chat - 3 patterns", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
async def index():
    return FileResponse(STATIC / "index.html")


# ---------------------------------------------------------------------------
# Implementation 1: Polling
# ---------------------------------------------------------------------------
@app.post("/api/polling/start")
async def polling_start(req: Request):
    body = await req.json()
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(400, "prompt required")
    job = Job(prompt)
    JOBS[job.id] = job
    asyncio.create_task(_run_job(job))
    return {"job_id": job.id}


@app.get("/api/polling/status/{job_id}")
async def polling_status(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    elapsed_ms = round((time.time() - job.started_at) * 1000)
    return {"status": job.status, "elapsed_ms": elapsed_ms, "error": job.error}


@app.get("/api/polling/result/{job_id}")
async def polling_result(job_id: str):
    job = JOBS.get(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    if job.status != "done":
        raise HTTPException(409, f"job not done (status={job.status})")
    return {"result": job.result}


# ---------------------------------------------------------------------------
# Implementation 2: Server-Sent Events
# ---------------------------------------------------------------------------
async def _llm_event_stream(prompt: str):
    """Async generator producing SSE-formatted bytes."""
    # opening event so the UI knows the stream is alive
    yield "event: open\ndata: streaming\n\n"
    try:
        stream = await client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                # Escape newlines because each SSE `data:` line is one line of text
                safe = delta.replace("\n", "\\n")
                yield f"event: token\ndata: {safe}\n\n"
        yield "event: done\ndata: complete\n\n"
    except Exception as exc:
        yield f"event: error\ndata: {str(exc)}\n\n"


@app.post("/api/sse/chat")
async def sse_chat(req: Request):
    body = await req.json()
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(400, "prompt required")
    return StreamingResponse(
        _llm_event_stream(prompt),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",   # disable nginx buffering if any
        },
    )


# ---------------------------------------------------------------------------
# Implementation 3: WebSocket
# ---------------------------------------------------------------------------
@app.websocket("/api/ws/chat")
async def ws_chat(websocket: WebSocket):
    """Bidirectional chat. Client sends:
        {"type": "prompt", "text": "..."}      → start streaming
        {"type": "interrupt"}                  → cancel mid-stream
    Server sends:
        {"type": "token", "text": "..."}
        {"type": "done"}
        {"type": "error", "message": "..."}
    """
    await websocket.accept()
    current_task: asyncio.Task | None = None

    async def stream_response(prompt: str):
        try:
            stream = await client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    await websocket.send_json({"type": "token", "text": delta})
            await websocket.send_json({"type": "done"})
        except asyncio.CancelledError:
            await websocket.send_json({"type": "interrupted"})
            raise
        except Exception as exc:
            await websocket.send_json({"type": "error", "message": str(exc)})

    try:
        while True:
            msg = await websocket.receive_json()
            mtype = msg.get("type")
            if mtype == "prompt":
                # cancel any existing stream first
                if current_task and not current_task.done():
                    current_task.cancel()
                prompt = (msg.get("text") or "").strip()
                if prompt:
                    current_task = asyncio.create_task(stream_response(prompt))
            elif mtype == "interrupt":
                if current_task and not current_task.done():
                    current_task.cancel()
    except WebSocketDisconnect:
        if current_task and not current_task.done():
            current_task.cancel()


# ---------------------------------------------------------------------------
# Convenience: a JSON list of endpoints for the UI to show
# ---------------------------------------------------------------------------
@app.get("/api/about")
def about():
    return JSONResponse({
        "model": MODEL,
        "endpoints": {
            "polling": ["POST /api/polling/start", "GET /api/polling/status/{id}", "GET /api/polling/result/{id}"],
            "sse": ["POST /api/sse/chat"],
            "ws": ["WS /api/ws/chat"],
        },
    })
