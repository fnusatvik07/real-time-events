# 06 - WebSockets (Swiggy/UberEats-style driver<->customer chat)

Realistic scenario: Raj's chicken biryani is on the way. He needs to tell rider Sam that the buzzer is broken and to call him. Sam needs to confirm ETA. Both sides have to be able to send AND receive messages at any time.

SSE wouldn't work (server-to-client only). Polling would be terrible (each message takes ~poll_interval to be seen). This is the textbook WebSocket fit.

## What the server does

`WS /chat?role=customer|driver&order=<id>`:
- Either party connects with their role and the order id (which acts as the chat "room")
- Both parties connecting with the same order id join the same room
- Each `{"type":"msg","text":"..."}` message is broadcast to everyone in the room
- Typing indicators and presence updates flow on the same connection

## Run

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

Each client sends a scripted set of messages with realistic delays. The output on each terminal shows messages flowing in both directions live.

## What you'll see

In the **customer** terminal:

```
==> Demo 2: Chat is live - watch the messages flow in both directions

  PRESENCE  driver joined the chat
  TYPING    driver is typing...
  TYPING    driver is not typing...
  RECV      driver   Hi Raj! I just picked up your order. 6 minutes away.
  SENT      me ->    Hi Sam! Are you nearby?
  TYPING    driver is typing...
  RECV      driver   Got it, will call when I arrive.
  SENT      me ->    Apartment 5C. The buzzer is broken - please call me at 9876543210
  RECV      driver   Reaching in 1 min. Looking for blue shirt.
  SENT      me ->    I'm waiting downstairs in a blue shirt.
  SENT      me ->    Thanks! 5 star rating coming your way.
```

And the **driver** terminal sees the mirror image (their own SENT lines and the customer's RECV lines).

## Talking points

- **One TCP connection, many messages.** Compare with HTTP where each message is its own request/response. With WebSockets the connection stays open for the entire conversation.
- **Symmetric send/receive.** Both sides have the same API. Compare with SSE where only the server can push.
- **Typing indicators are basically free.** They're just small extra messages on the same channel.
- **Scaling.** A single Python process can hold ~10-50K open WS connections with tuning. Past that you need a pub-sub backbone (Redis) so messages broadcast across multiple servers.

## Test broadcast with a third party

Open a fourth terminal and connect a **second customer** to the same order:

```bash
python client.py --role customer --order order_raj_001
```

Now there are 3 clients in the room. Every message goes to all 3. This shows broadcast scaling naturally - the server just iterates its in-memory list of connections.

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
