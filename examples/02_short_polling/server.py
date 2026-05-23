"""Short polling demo - Swiggy-style food order tracker.

A small "order service" that lets you place an order and then check its
status. The order advances through realistic stages in the background:

    placed (0s)
       -> restaurant_confirmed   (5 sec after placed)
       -> preparing              (8 sec after confirmed)
       -> rider_assigned         (5 sec after preparing started)
       -> picked_up              (7 sec after rider assigned)
       -> out_for_delivery       (6 sec after picked up)
       -> delivered              (10 sec after out for delivery)

The client (next door in client.py) polls /orders/{id} on a fixed timer
and visualises how many polls were wasted.

Run:
    uvicorn server:app --port 8102
"""
from __future__ import annotations

import asyncio
import random
import string
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Order state machine
# ---------------------------------------------------------------------------
STAGES = [
    ("placed",                "Order placed - waiting for restaurant"),
    ("restaurant_confirmed",  "Restaurant accepted the order"),
    ("preparing",             "Restaurant is preparing your food"),
    ("rider_assigned",        "Rider Sam is on the way to the restaurant"),
    ("picked_up",             "Rider Sam has picked up your order"),
    ("out_for_delivery",      "On the way to you"),
    ("delivered",             "Delivered. Enjoy!"),
]

# Seconds between transitions. Tuned so the whole flow happens in ~40s
# and a 1.5s poll interval will visibly waste polls between transitions.
DELAYS = [5, 8, 5, 7, 6, 10]


class Order(BaseModel):
    id: str
    customer: str
    item: str
    amount_inr: int
    status: str
    status_label: str
    created_at: float
    last_updated_at: float


class CreateOrderRequest(BaseModel):
    customer: str = "Raj"
    item: str = "Chicken Biryani"
    amount_inr: int = 450


# in-memory store
orders: dict[str, Order] = {}
advancing_tasks: dict[str, asyncio.Task] = {}


def new_id() -> str:
    return "ord_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=8))


async def advance_order(order_id: str):
    """Background task that walks an order through the stages with delays."""
    try:
        for stage_index, delay in enumerate(DELAYS, start=1):
            await asyncio.sleep(delay)
            order = orders.get(order_id)
            if not order:
                return
            stage, label = STAGES[stage_index]
            order.status = stage
            order.status_label = label
            order.last_updated_at = time.time()
    except asyncio.CancelledError:
        pass


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    # cancel any in-flight order tasks on shutdown
    for t in advancing_tasks.values():
        t.cancel()


app = FastAPI(title="Swiggy-style order service", lifespan=lifespan)


@app.get("/")
def root():
    return {
        "service": "Swiggy-style order tracker",
        "endpoints": {
            "POST /orders":        "place an order (returns order id)",
            "GET  /orders/{id}":   "get current status of an order",
            "GET  /orders":        "list all in-memory orders (debug)",
        },
        "stages": [s[0] for s in STAGES],
    }


@app.post("/orders", status_code=201)
async def create_order(req: CreateOrderRequest):
    order_id = new_id()
    now = time.time()
    order = Order(
        id=order_id,
        customer=req.customer,
        item=req.item,
        amount_inr=req.amount_inr,
        status=STAGES[0][0],
        status_label=STAGES[0][1],
        created_at=now,
        last_updated_at=now,
    )
    orders[order_id] = order
    # kick off the background state-machine
    advancing_tasks[order_id] = asyncio.create_task(advance_order(order_id))
    return order


@app.get("/orders/{order_id}")
def get_order(order_id: str):
    order = orders.get(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"order {order_id} not found")
    return order


@app.get("/orders")
def list_orders():
    return {"count": len(orders), "orders": list(orders.values())}
