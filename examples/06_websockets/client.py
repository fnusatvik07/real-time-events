"""WebSocket client - Raj <-> rider Sam chat over a delivery.

Two modes:

  default (interactive)   --  you TYPE messages and press Enter. Each line
                              is sent as a chat message. Incoming messages
                              from the other side appear above your prompt
                              live. This is the mode for live class demos.

  --script                --  fires a small pre-written timeline of messages.
                              Useful for QA, or for a solo run when you want
                              both sides to behave without a second person at
                              the keyboard.

Run TWO copies side-by-side in two terminals so they can chat with each
other through the server.

    Terminal 1 (server):
        uvicorn server:app --port 8106

    Terminal 2 (customer Raj):
        python client.py --role customer

    Terminal 3 (rider Sam):
        python client.py --role driver

    Now type in either terminal and watch it appear in the other.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _pretty import (
    banner, demo, divider,
    lesson, note, info, ok, warn, preflight_check,
    GREEN, CYAN, YELLOW, MAGENTA, BLUE, RED, DIM, BOLD, RESET, event,
)

import websockets

URL_TEMPLATE = "ws://127.0.0.1:8106/chat?role={role}&order={order}"

# Pre-written timelines (used in --script mode only)
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


def _color_for(role: str) -> str:
    return GREEN if role == "customer" else BLUE


def _print_above_prompt(line: str, is_interactive: bool) -> None:
    """Print an incoming line. In interactive mode, also redraw the prompt."""
    if is_interactive:
        # \r returns to start of line, the line itself, then re-show the prompt
        print(f"\r{line}")
        print(f"  {DIM}> {RESET}", end="", flush=True)
    else:
        print(line)


async def reader(ws, my_role: str, is_interactive: bool):
    """Print every message we receive, color-coded by sender."""
    try:
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
                    # echo of our own send (server broadcasts to all in room)
                    _print_above_prompt(
                        f"  {DIM}-> me        {text}{RESET}",
                        is_interactive,
                    )
                else:
                    color = _color_for(sender)
                    _print_above_prompt(
                        f"  {color}{BOLD}<- {sender:9s}{RESET}{color} {text}{RESET}",
                        is_interactive,
                    )
            elif mtype == "presence":
                ic = GREEN if msg.get("online") else YELLOW
                _print_above_prompt(
                    f"  {ic}* {msg['text']}{RESET}",
                    is_interactive,
                )
            elif mtype == "system":
                _print_above_prompt(
                    f"  {DIM}~ {msg['text']}{RESET}",
                    is_interactive,
                )
            elif mtype == "typing":
                who = msg["from"]
                is_typing = msg.get("on")
                if is_typing:
                    _print_above_prompt(
                        f"  {DIM}({who} is typing...){RESET}",
                        is_interactive,
                    )
    except websockets.ConnectionClosed:
        pass


async def interactive_writer(ws, role: str):
    """Read user input line-by-line, send each line as a chat message."""
    loop = asyncio.get_event_loop()
    print(f"  {DIM}> {RESET}", end="", flush=True)
    while True:
        try:
            line = await loop.run_in_executor(
                None, sys.stdin.readline
            )
        except (EOFError, KeyboardInterrupt):
            return
        if line == "":   # stdin closed
            return
        text = line.rstrip("\n").strip()
        if not text:
            print(f"  {DIM}> {RESET}", end="", flush=True)
            continue
        if text.lower() in ("/q", "/quit", "exit"):
            print(f"  {DIM}leaving...{RESET}")
            return
        if text == "/typing":
            await ws.send(json.dumps({"type": "typing", "on": True}))
            await asyncio.sleep(1.5)
            await ws.send(json.dumps({"type": "typing", "on": False}))
            print(f"  {DIM}> {RESET}", end="", flush=True)
            continue
        await ws.send(json.dumps({"type": "msg", "text": text}))
        # Don't print the prompt yet - the server will broadcast our own
        # message back as a "-> me" line, and reader() will print the prompt.


async def scripted_writer(ws, role: str):
    """Fire a pre-written timeline. Used by --script mode (QA, solo demos)."""
    await asyncio.sleep(0.5)
    script = SCRIPTS.get(role, [])
    for delay, text in script:
        await asyncio.sleep(delay)
        await ws.send(json.dumps({"type": "typing", "on": True}))
        await asyncio.sleep(0.8)
        await ws.send(json.dumps({"type": "typing", "on": False}))
        await ws.send(json.dumps({"type": "msg", "text": text}))
    # Hang around a bit so we receive any final messages from the other side.
    await asyncio.sleep(6)


async def main(role: str, order: str, scripted: bool):
    preflight_check("http://127.0.0.1:8106", expected_keyword="delivery chat")
    url = URL_TEMPLATE.format(role=role, order=order)

    banner(
        f"WebSocket delivery chat - role = {role}",
        f"connecting to {url}",
    )

    demo(1, "Open the WebSocket connection")
    info(f"role:   {role}")
    info(f"order:  {order}")
    info(f"mode:   {'SCRIPTED (auto-fires messages)' if scripted else 'INTERACTIVE (type and press Enter)'}")
    print()

    try:
        ws_conn = await websockets.connect(url)
    except OSError as e:
        print(f"  {RED}{BOLD}ERROR{RESET}   could not connect to {url}")
        print(f"            ({e})")
        print(f"            is the server running on port 8106?")
        sys.exit(1)

    async with ws_conn as ws:
        ok(f"connected as {role}")
        print()
        if scripted:
            note("scripted mode - both sides fire pre-written messages on a timer")
        else:
            note("interactive mode - type a message and press ENTER to send")
            note("special commands:  /typing  (send typing indicator),  /q  (quit)")
            note("OPEN A SECOND TERMINAL with the OTHER role to see live chat both ways")
        divider()
        print()

        reader_task = asyncio.create_task(reader(ws, role, is_interactive=not scripted))
        if scripted:
            writer_task = asyncio.create_task(scripted_writer(ws, role))
        else:
            writer_task = asyncio.create_task(interactive_writer(ws, role))

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
        "Both sides used send and receive symmetrically over ONE TCP "
        "connection. Compare with SSE (example 05) where the client could "
        "only listen. The WebSocket connection stayed open between "
        "messages - the server didn't reconnect for each event."
    )
    print()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--role", default="customer", choices=("customer", "driver"))
    p.add_argument("--order", default="order_raj_001")
    p.add_argument(
        "--script",
        action="store_true",
        help="run the pre-written timeline instead of reading from stdin "
             "(used by qa.sh and for solo demos)",
    )
    args = p.parse_args()

    asyncio.run(main(args.role, args.order, scripted=args.script))
