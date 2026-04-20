import asyncio
import websockets

clients = set()

async def handler(websocket):
    print("Client connected")
    clients.add(websocket)

    try:
        async for message in websocket:
            print("Received:", message)

            for client in clients:
                # if client != websocket:
                #     await client.send(message)
                await client.send(message)

    except:
        pass

    finally:
        clients.remove(websocket)
        print("Client disconnected")


async def main():
    async with websockets.serve(handler, "0.0.0.0", 8765):
        print("WebSocket server loaded: ws://0.0.0.0:8765")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())