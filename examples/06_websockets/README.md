# 06 - WebSockets

Full-duplex: both sides can send messages anytime over one persistent connection.

This example is an echo+broadcast server. Run two clients in parallel and you'll see each receive the other's messages.

## Run

**Terminal 1:**
```bash
cd examples/06_websockets
uvicorn server:app --port 8106
```

**Terminal 2** (one client):
```bash
cd examples/06_websockets
python client.py
```

**Terminal 3** (optional - second client, for the broadcast effect):
```bash
cd examples/06_websockets
python client.py
```

## Expected output (one client)

```
connecting to ws://127.0.0.1:8106/ws ...
connected (HTTP upgraded to WebSocket)

  SEND: 'hello'
  RECV: [from 1234] hello
  SEND: 'world'
  RECV: [from 1234] world
  SEND: 'real-time!'
  RECV: [from 1234] real-time!

closing connection
```

## Try it from the browser console

Open any web page, open the console, and run:
```javascript
const ws = new WebSocket('ws://127.0.0.1:8106/ws');
ws.onmessage = e => console.log('RECV:', e.data);
ws.onopen = () => ws.send('hi from browser');
```

## What to point out

- The connection started as an HTTP request (`GET /ws  Upgrade: websocket`) and then "upgraded" to a custom protocol. After that no more HTTP - just frames either side can send.
- **Symmetric API.** Server uses `send`/`receive`, client uses `send`/`recv`. Either can talk first.
- For a single one-way stream, SSE is simpler. WebSocket pays off when you need bidirectional (chat, voice, interruption, games).
- Scaling note: every connected client = one held TCP socket. 100k clients = real RAM. Don't reach for WS when SSE would do.
