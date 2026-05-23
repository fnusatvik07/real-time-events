"""WebSocket client - Raj <-> rider Sam chat over a delivery.

Run TWO copies side-by-side. One as customer, one as driver. They'll
both connect to the same chat room and exchange messages live.

    Terminal 1 (server):
        uvicorn server:app --port 8106

    Terminal 2 (customer Raj):
        python client.py --role customer

    Terminal 3 (rider Sam):
        python client.py --role driver

Each client sends a small scripted conversation with realistic delays so
the audience can see messages arrive on the OTHER terminal live.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _pretty import (
    banner, demo, divider,
    lesson, note, info, ok, preflight_check,
    GREEN, CYAN, YELLOW, MAGENTA, BLUE, DIM, BOLD, RESET, event,
)

import websockets

URL_TEMPLATE = "ws://127.0.0.1:8106/chat?role={role}&order={order}"
preflight_check("http://127.0.0.1:8106", expected_keyword="delivery chat")


# Scripted scenarios. Each entry is (delay_before_sending, text).
SCRIPTS = {
    "customer": [
        (1.5, "Hi Sam! Are you nearby?"),
        (4.0, "Apartment 5C. The buzzer is broken - please call me at 9876543210"),
        (3.5, "I'm waiting downstairs in a blue shirt."),
        (3.0, "Thanks! 5 star rating coming your way."),
    ],
    "driver": [
        (2.5, "Hi Raj! I just picked up your order. 6 minutes away."),
        (3.0, "Got it, will call when I arrive."),
        (5.0, "Reaching in 1 min. Looking for blue shirt."),
    ],
}


async def reader(ws, my_role: str):
    """Print every message we receive, color-coded by sender."""
    async for raw in ws:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue
        mtype = msg.get("type")

        if mtype == "msg":
            sender = msg["from"]
            text = msg["text"]
            if sender == my_role:
                # echo of my own message (server broadcast includes sender)
                event("SENT", f"{DIM}me ->{RESET} {text}", color=DIM)
            else:
                color = GREEN if sender == "customer" else BLUE
                event("RECV", f"{color}{BOLD}{sender:8s}{RESET} {text}", color=CYAN)

        elif mtype == "presence":
            color = GREEN if msg["online"] else YELLOW
            event("PRESENCE", f"{color}{msg['text']}{RESET}", color=color)

        elif mtype == "system":
            event("SYSTEM", f"{DIM}{msg['text']}{RESET}", color=DIM)

        elif mtype == "typing":
            who = msg["from"]
            on = msg["on"]
            event("TYPING", f"{DIM}{who} is{' ' if on else ' not '}typing...{RESET}", color=DIM)


async def writer(ws, role: str):
    """Send our scripted lines with delays."""
    await asyncio.sleep(0.5)  # let the reader print "connected" first

    script = SCRIPTS.get(role, [])
    for delay, text in script:
        await asyncio.sleep(delay)

        # typing indicator on
        await ws.send(json.dumps({"type": "typing", "on": True}))
        await asyncio.sleep(0.8)
        # typing indicator off
        await ws.send(json.dumps({"type": "typing", "on": False}))

        # the actual message
        await ws.send(json.dumps({"type": "msg", "text": text}))

    # leave the connection open a bit so we receive any final replies
    await asyncio.sleep(6)


async def main(role: str, order: str):
    url = URL_TEMPLATE.format(role=role, order=order)

    banner(
        f"WebSocket delivery chat - role = {role}",
        f"connecting to {url}",
    )

    demo(1, "Open the WebSocket connection")
    info(f"role:  {role}")
    info(f"order: {order}")
    print()

    async with websockets.connect(url) as ws:
        ok(f"connected as {role}")
        print()
        demo(2, "Chat is live - watch the messages flow in both directions")
        print()

        reader_task = asyncio.create_task(reader(ws, role))
        writer_task = asyncio.create_task(writer(ws, role))

        try:
            await writer_task
        finally:
            reader_task.cancel()
            try:
                await reader_task
            except asyncio.CancelledError:
                pass

    print()
    divider()
    lesson(
        "Both sides used send() and receive() symmetrically over ONE TCP "
        "connection. Compare with SSE (example 05) where the client could "
        "only listen. The WebSocket connection stayed open between "
        "messages - the server didn't reconnect for each event."
    )
    print()
    print(f"  Open a second terminal and run with the OTHER role to see the chat from")
    print(f"  the other side. Both clients see each other's messages instantly.")
    print()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--role", default="customer", choices=("customer", "driver"))
    p.add_argument("--order", default="order_raj_001")
    args = p.parse_args()

    asyncio.run(main(args.role, args.order))
