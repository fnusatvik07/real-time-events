"""WebSocket server - Swiggy/UberEats-style driver <-> customer chat.

When Raj's order is on its way, the app lets Raj and the rider chat in
real-time about details (buzzer code, "leave at door", etc.). Both sides
can send and receive messages at any time. SSE wouldn't work because
the customer needs to send too. This is the classic WebSocket fit.

Endpoints:
  GET  /                   info page
  GET  /sessions           debug: list active chat sessions
  WS   /chat?role=...&order=...
       role is "customer" or "driver"
       order identifies the chat room
       both sides connecting to the same order join the same room

Message shapes:
  inbound (client -> server):  {"type": "msg", "text": "..."}
                               {"type": "typing", "on": true}
  outbound (server -> client): {"type": "msg", "from": "customer", "text": "...", "ts": ...}
                               {"type": "presence", "user": "driver", "online": true}
                               {"type": "system", "text": "rider Sam has joined"}

Run:
    uvicorn server:app --port 8106
"""
from __future__ import annotations

import asyncio
import json
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(title="Delivery chat (driver <-> customer)")

# rooms[order_id] = list of (role, websocket)
rooms: dict[str, list[tuple[str, WebSocket]]] = {}


@app.get("/")
def root():
    return {
        "service": "Swiggy/UberEats-style delivery chat",
        "endpoints": {
            "GET  /sessions":            "debug list of active rooms",
            "WS   /chat?role=&order=":   "open a chat as 'customer' or 'driver' for an order",
        },
        "examples": [
            "ws://127.0.0.1:8106/chat?role=customer&order=order_raj_001",
            "ws://127.0.0.1:8106/chat?role=driver&order=order_raj_001",
        ],
    }


@app.get("/sessions")
def sessions():
    return {
        "rooms": {oid: [r for r, _ in members] for oid, members in rooms.items()}
    }


async def broadcast(order_id: str, msg: dict, exclude: WebSocket | None = None):
    payload = json.dumps(msg)
    dead: list[tuple[str, WebSocket]] = []
    for role, ws in rooms.get(order_id, []):
        if ws is exclude:
            continue
        try:
            await ws.send_text(payload)
        except Exception:
            dead.append((role, ws))
    for entry in dead:
        try:
            rooms[order_id].remove(entry)
        except ValueError:
            pass


@app.websocket("/chat")
async def chat(websocket: WebSocket, role: str = "customer", order: str = "order_default"):
    await websocket.accept()

    if role not in ("customer", "driver"):
        await websocket.close(code=4001, reason="role must be customer or driver")
        return

    rooms.setdefault(order, []).append((role, websocket))
    other_side = "rider Sam" if role == "customer" else "customer Raj"

    print(f"[ws]  {role:8s} joined order {order}  ({len(rooms[order])} in room)")

    # Tell the new joiner who else is here
    other_present = any(r != role for r, _ in rooms[order])
    await websocket.send_text(json.dumps({
        "type": "system",
        "text": f"connected as {role}. " +
                (f"{other_side} is online." if other_present else f"{other_side} is not connected yet."),
    }))
    # Tell everyone else that this party joined
    await broadcast(order, {
        "type": "presence",
        "user": role,
        "online": True,
        "text": f"{role} joined the chat",
    }, exclude=websocket)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            mtype = msg.get("type")

            if mtype == "msg":
                out = {
                    "type": "msg",
                    "from": role,
                    "text": msg.get("text", ""),
                    "ts": time.time(),
                }
                # broadcast to room (including the sender as an ack)
                await broadcast(order, out)

            elif mtype == "typing":
                await broadcast(order, {
                    "type": "typing",
                    "from": role,
                    "on": bool(msg.get("on")),
                }, exclude=websocket)

    except WebSocketDisconnect:
        pass
    finally:
        try:
            rooms[order].remove((role, websocket))
        except ValueError:
            pass
        await broadcast(order, {
            "type": "presence",
            "user": role,
            "online": False,
            "text": f"{role} left the chat",
        })
        print(f"[ws]  {role:8s} left   order {order}  ({len(rooms.get(order, []))} in room)")
