"""Long polling demo server.

A background task bumps the counter every 5 seconds.
GET /wait?since=N holds the request until counter > N (or 10s timeout).

Run: uvicorn server:app --port 8103
"""
import asyncio
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI

state = {"counter": 0}


async def bumper():
    while True:
        await asyncio.sleep(5)
        state["counter"] += 1
        print(f"  [server] bumped counter -> {state['counter']}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    t = asyncio.create_task(bumper())
    yield
    t.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/wait")
async def wait(since: int = 0, timeout: float = 10.0):
    """Hold the request until counter > since, or until timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if state["counter"] > since:
            return {"counter": state["counter"], "timed_out": False}
        await asyncio.sleep(0.05)
    return {"counter": state["counter"], "timed_out": True}
