"""WebSocket client - opens one persistent connection, sends 3 messages.

Try running TWO copies in parallel - each will receive the other's messages
because the server broadcasts.
"""
import asyncio
import websockets

URL = "ws://127.0.0.1:8106/ws"


async def main():
    print(f"connecting to {URL} ...")
    async with websockets.connect(URL) as ws:
        print("connected (HTTP upgraded to WebSocket)\n")

        # Background task: keep printing any messages we receive
        async def reader():
            try:
                async for msg in ws:
                    print(f"  RECV: {msg}")
            except websockets.ConnectionClosed:
                pass

        reader_task = asyncio.create_task(reader())

        for msg in ["hello", "world", "real-time!"]:
            print(f"  SEND: {msg!r}")
            await ws.send(msg)
            await asyncio.sleep(0.3)  # leave time for the broadcast to come back

        await asyncio.sleep(0.5)
        reader_task.cancel()
        print("\nclosing connection")


asyncio.run(main())

print("\nKey observations:")
print("  - ONE connection used for ALL messages (not 3 separate HTTP requests)")
print("  - Both directions worked on the same connection (we sent AND received)")
print("  - Try running TWO copies of this script in parallel - broadcast!")
