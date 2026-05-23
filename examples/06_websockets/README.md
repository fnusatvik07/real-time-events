# 06 - WebSockets (Swiggy/UberEats-style driver<->customer chat)

Realistic scenario: Raj's chicken biryani is on the way. He needs to tell rider Sam that the buzzer is broken and to call him. Sam needs to confirm ETA. Both sides have to be able to send AND receive messages at any time.

SSE wouldn't work (server-to-client only). Polling would be terrible (each message takes ~poll_interval to be seen). This is the textbook WebSocket fit.

## Two modes

The client supports two modes:

| Mode | Flag | Use it for |
|------|------|-----------|
| **Interactive** (default) | (none) | **Live class demo.** You actually type messages and the other side sees them. Real conversation. |
| **Scripted** | `--script` | Solo run / QA. Each side fires a pre-written timeline on a timer, no typing needed. |

For teaching, use **interactive**. The whole point of WebSockets is that both sides can talk anytime - prove it by actually typing.

## Run (interactive - the demo)

**Terminal 1** (the server):
```bash
cd examples/06_websockets
uvicorn server:app --port 8106
```

**Terminal 2** (customer Raj):
```bash
cd examples/06_websockets
python client.py --role customer
```

**Terminal 3** (rider Sam) - run this **in parallel** with Terminal 2:
```bash
cd examples/06_websockets
python client.py --role driver
```

Now type in either terminal and press Enter. The message appears in BOTH terminals (the sender sees `-> me ...`, the other side sees `<- customer ...` or `<- driver ...`).

Special commands at the prompt:

| Type | What it does |
|------|-------------|
| any text + Enter | Sends as a chat message |
| `/typing` + Enter | Sends a typing indicator (the other side sees "customer is typing...") |
| `/q` + Enter | Disconnect and exit |

## What a live demo looks like

In the **customer** terminal:

```
  * driver joined the chat
  > Hi Sam, are you nearby?_
```

You type. You press Enter. Meanwhile in the **driver** terminal:

```
  <- customer  Hi Sam, are you nearby?
  > _
```

Driver types `5 min, picking up your order now` and presses Enter. In the **customer** terminal:

```
  -> me        Hi Sam, are you nearby?
  <- driver    5 min, picking up your order now
  > _
```

Both terminals scrolling live. That's the WebSocket demo - real bidirectional traffic, no polling, no special infrastructure, all over one TCP connection.

## Run (scripted - for QA or solo)

If you don't have a second person at the keyboard, scripted mode is fine:

```bash
# Terminal 2:
python client.py --role customer --script

# Terminal 3:
python client.py --role driver --script
```

Each side fires its pre-written timeline. You'll see realistic chat output without typing anything. Same protocol on the wire.

## What the server does

`WS /chat?role=customer|driver&order=<id>`:

- Either party connects with their role and the order id (which is the chat "room")
- Both parties connecting with the same order id join the same room
- Each `{"type":"msg","text":"..."}` message is broadcast to everyone in the room (including the sender, so the sender's UI can confirm "your message was delivered")
- Typing indicators and presence updates flow on the same connection

## Talking points

- **One TCP connection, many messages.** Compare with HTTP where each message is its own request/response. With WebSockets the connection stays open for the entire conversation.
- **Symmetric send/receive.** Both sides have the same API. Compare with SSE where only the server can push.
- **Typing indicators are basically free.** They're just small extra messages on the same channel.
- **The server's job is small.** Verify auth on connect, track who's in which room, forward messages. ~30 lines of code.
- **Scaling.** A single Python process holds ~10-50K open WS connections with tuning. Past that you need a pub-sub backbone (Redis) so messages broadcast across multiple servers.

## Test broadcast with a third party

Open a fourth terminal and connect a **second customer** to the same order:

```bash
python client.py --role customer --order order_raj_001
```

Now there are 3 clients in the room. Every message goes to all 3. This shows broadcast scaling naturally.

## Try it from the browser console

Open any web page, open the console, paste:

```javascript
const ws = new WebSocket('ws://127.0.0.1:8106/chat?role=customer&order=test_room');
ws.onmessage = e => console.log('RECV:', JSON.parse(e.data));
ws.onopen = () => ws.send(JSON.stringify({type:'msg', text:'hi from browser'}));
```

You're now in the chat room.

## Where this pattern shows up

- WhatsApp, Telegram, Signal (chat messaging)
- Slack, Discord, Microsoft Teams
- Google Docs, Figma, Notion (live cursors and collaborative editing)
- Multiplayer browser games
- Trading platforms (live orderbook + order submission)
- Voice agents (OpenAI Realtime API, Vapi, Retell)
- Cursor / GitHub Copilot Chat
