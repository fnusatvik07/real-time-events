"""SSE server - streams 10 events over one HTTP connection.

Run: uvicorn server:app --port 8105
"""
import asyncio
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()


@app.get("/")
def root():
    return {"ok": True}


@app.get("/stream")
async def stream():
    """Returns 10 events spaced 300ms apart, then a 'done' event."""
    async def gen():
        for i in range(10):
            # SSE wire format:
            #   id: <id>           (optional, enables Last-Event-ID resume)
            #   event: <name>      (optional, defaults to 'message')
            #   data: <payload>    (one or more lines)
            #   <blank line>       (end of event)
            yield f"id: {i}\nevent: token\ndata: token-{i}\n\n"
            await asyncio.sleep(0.3)
        yield "event: done\ndata: stream complete\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
