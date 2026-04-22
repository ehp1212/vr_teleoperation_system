import asyncio
import json
import websockets

clients = {
    "pc": None,
    "headset": None
}

async def handler(websocket):
    role = None

    try: 
        register_msg = await websocket.recv()
        register_data = json.loads(register_msg)

        role = register_data.get("role")
        if not role:
            print(f"Invalid role is trying to access")
            return
        
        if role not in clients:
            await websocket.close()
            return

        clients[role] = websocket
        print(f"[Connected] {role}")

        # Message Loop
        async for message in websocket:
            data = json.loads(message)

            sender = data.get("from")
            if sender not in ["pc", "headset"]:
                print("Invalid sender:", sender)
                continue

            target = "headset" if sender == "pc" else "pc"

            target_ws = clients.get(target)
            if target_ws:
                await target_ws.send(json.dumps(data))
                print(f"[RELAY] {sender} -> {target} | {data['type']}")
            else:
                print(f"[WARN] target {target} not connected")

    except websockets.exceptions.ConnectionClosed:
        print(f"[DISCONNECTED] {role}")
    finally:
        if role:
            clients[role] = None

async def main():
    print(f"Signalling Server started")

    async with websockets.serve(handler, "0.0.0.0", 8765):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())