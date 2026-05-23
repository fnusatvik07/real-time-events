"""Short polling demo server.

A background task bumps a `counter` every 5 seconds.
Clients poll /value to see what it is right now.

Run: uvicorn server:app --port 8102
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

state = {"counter": 0, "last_bumped_at": 0.0}


async def bumper():
    """Bump the counter every 5 seconds so we have something to poll for."""
    import time
    while True:
        await asyncio.sleep(5)
        state["counter"] += 1
        state["last_bumped_at"] = time.time()
        print(f"  [server] bumped counter -> {state['counter']}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(bumper())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


@app.get("/value")
def get_value():
    return {"counter": state["counter"]}
