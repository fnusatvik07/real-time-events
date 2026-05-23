"""Long polling demo - Uber-style ride dispatch.

When a rider requests a ride, the app shows "Looking for a driver..." and
hangs there until a driver accepts. The client only needs ONE long-poll
request - the server holds it open and replies the instant a driver is
matched (or after a 30-second timeout).

Endpoints:
  POST /rides                  create a ride request (returns ride_id)
  GET  /rides/{id}/wait        long-poll: hold until driver assigned, or 30s timeout
  GET  /rides/{id}             current snapshot (used as fallback / debug)

A background task simulates a driver accepting after a random 4-12 seconds.

Run:
    uvicorn server:app --port 8103
"""
from __future__ import annotations

import asyncio
import random
import string
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
DRIVERS = [
    {"name": "Sam",   "vehicle": "TN-09-AB-1234", "rating": 4.9, "eta_min": 4},
    {"name": "Priya", "vehicle": "KA-05-CD-5678", "rating": 4.8, "eta_min": 3},
    {"name": "Ravi",  "vehicle": "MH-12-EF-9012", "rating": 4.7, "eta_min": 6},
    {"name": "Anita", "vehicle": "DL-08-GH-3456", "rating": 4.9, "eta_min": 5},
]


class RideRequest(BaseModel):
    rider: str = "Raj"
    pickup: str = "Indiranagar Metro Station"
    dropoff: str = "Bengaluru Airport"


class Ride:
    def __init__(self, ride_id: str, req: RideRequest):
        self.id = ride_id
        self.rider = req.rider
        self.pickup = req.pickup
        self.dropoff = req.dropoff
        self.status = "searching"          # searching | accepted
        self.driver: dict | None = None
        self.created_at = time.time()
        # Event that the long-poll handler awaits
        self.accepted_event = asyncio.Event()


rides: dict[str, Ride] = {}


def new_id() -> str:
    return "ride_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


async def simulate_driver_match(ride_id: str):
    """After a random delay, mark the ride as accepted by a driver."""
    delay = random.uniform(4, 12)
    await asyncio.sleep(delay)
    ride = rides.get(ride_id)
    if not ride or ride.status != "searching":
        return
    ride.driver = random.choice(DRIVERS)
    ride.status = "accepted"
    ride.accepted_event.set()


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(title="Uber-style ride dispatch", lifespan=lifespan)


@app.get("/")
def root():
    return {
        "service": "Uber-style ride dispatch",
        "endpoints": {
            "POST /rides":              "create a ride request",
            "GET  /rides/{id}/wait":    "LONG POLL - hold until driver accepts (or 30s timeout)",
            "GET  /rides/{id}":         "current snapshot",
        },
    }


@app.post("/rides", status_code=201)
async def create_ride(req: RideRequest):
    ride_id = new_id()
    ride = Ride(ride_id, req)
    rides[ride_id] = ride
    asyncio.create_task(simulate_driver_match(ride_id))
    return {
        "id": ride.id,
        "status": ride.status,
        "rider": ride.rider,
        "pickup": ride.pickup,
        "dropoff": ride.dropoff,
        "message": "ride created. searching for nearby drivers...",
    }


@app.get("/rides/{ride_id}")
def get_ride(ride_id: str):
    ride = rides.get(ride_id)
    if not ride:
        raise HTTPException(404, f"ride {ride_id} not found")
    return _ride_response(ride)


@app.get("/rides/{ride_id}/wait")
async def wait_for_driver(ride_id: str, timeout: float = 30.0):
    """Long poll - hold the request open until a driver accepts.

    Returns immediately if the ride is already accepted (e.g. on a
    reconnect). Returns a timed_out flag if no driver appeared in time
    so the client knows to reconnect.
    """
    ride = rides.get(ride_id)
    if not ride:
        raise HTTPException(404, f"ride {ride_id} not found")

    if ride.status == "accepted":
        return _ride_response(ride)

    try:
        await asyncio.wait_for(ride.accepted_event.wait(), timeout=timeout)
        return _ride_response(ride)
    except asyncio.TimeoutError:
        return {**_ride_response(ride), "timed_out": True}


def _ride_response(ride: Ride) -> dict:
    return {
        "id": ride.id,
        "status": ride.status,
        "rider": ride.rider,
        "pickup": ride.pickup,
        "dropoff": ride.dropoff,
        "driver": ride.driver,
        "elapsed_sec": round(time.time() - ride.created_at, 1),
        "timed_out": False,
    }
