"""WebSocket echo + broadcast server.

Any message a client sends is echoed back to ALL connected clients.

Run: uvicorn server:app --port 8106
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()
clients: set[WebSocket] = set()


@app.get("/")
def root():
    return {"ok": True, "connected_clients": len(clients)}


@app.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    clients.add(websocket)
    me = id(websocket) % 10000
    print(f"  [server] client {me} connected ({len(clients)} total)")
    try:
        while True:
            msg = await websocket.receive_text()
            print(f"  [server] client {me} said: {msg!r}")
            # broadcast to everyone (including the sender)
            for c in list(clients):
                try:
                    await c.send_text(f"[from {me}] {msg}")
                except Exception:
                    clients.discard(c)
    except WebSocketDisconnect:
        clients.discard(websocket)
        print(f"  [server] client {me} disconnected ({len(clients)} total)")
