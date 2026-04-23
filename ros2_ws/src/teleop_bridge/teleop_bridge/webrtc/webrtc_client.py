import asyncio
import json
import websockets

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.sdp import candidate_from_sdp

from .rotation_processor import RotationProcessor
from .control_processor import ControlProcessor

class WebRTCClient:
    def __init__(self, teleop_node, isaac_image_track, hw_image_track):
        self.signaling_url = "ws://172.20.10.8:8765"

        self.teleop_node = teleop_node
        self.isaac_image_track = isaac_image_track
        self.hw_image_track = hw_image_track

        self.pc = None
        self.ws = None

        self.rotation_processor = RotationProcessor()
        self.control_processor = ControlProcessor()

        print(f"WebRTC client initialized: {self.signaling_url}")

    # =====================
    # Connect Loop
    # =====================
    async def connect_loop(self):
        while True:
            try:
                print("Connecting to signaling...")
                await self.connect_signaling()

            except Exception as e:
                print("Connection error:", e)

            print("retry in 2s...")
            await asyncio.sleep(2)

    # =====================
    # Signaling
    # =====================
    async def connect_signaling(self):
        self.pc = RTCPeerConnection()

        # Data channel
        control_channel = self.pc.createDataChannel("control")

        @control_channel.on("open")
        def on_open():
            print(f"DataChannel open")

        @control_channel.on("message")
        def on_message(message):
            data = json.loads(message)
            self.teleop_node.handle_message(data)
            
        @control_channel.on("close")
        def on_close():
            print(f"DataChannel close")

        # Track 
        self.pc.addTrack(self.isaac_image_track)
        # self.pc.addTrack(self.hw_image_track)

        # =====================
        # ICE candidate 
        # =====================
        @self.pc.on("icecandidate")
        async def on_icecandidate(candidate):
            if candidate is not None and self.ws is not None:
                msg = {
                    "type": "ice",
                    "candidate": candidate.to_sdp(),
                    "sdpMid": candidate.sdpMid,
                    "sdpMLineIndex": candidate.sdpMLineIndex,
                    "from": "pc"
                }
                await self.ws.send(json.dumps(msg))

        # =====================
        # connection state change
        # =====================
        @self.pc.on("connectionstatechange")
        async def on_state_change():
            print("Connection state:", self.pc.connectionState)

            if self.pc.connectionState in ["failed", "disconnected", "closed"]:
                await self.pc.close()
                raise Exception("WebRTC disconnected")

        # =====================
        # WebSocket
        # =====================
        async with websockets.connect(self.signaling_url) as ws:
            self.ws = ws
            print("Connected to signaling server")

            await self.ws.send(json.dumps(
                {
                    "role": "pc",
                    "from": "pc"
                }
            ))

            ready = False

            # =====================
            # message loop
            # =====================
            async for raw_msg in ws:
                data = json.loads(raw_msg)
                msg_type = data.get("type")

                # ---------------------
                # WAIT FOR READY 
                # ---------------------
                if not ready:
                    if msg_type == "ready":
                        print("Headset ready")
                        ready = True

                        # Offer 
                        offer = await self.pc.createOffer()
                        await self.pc.setLocalDescription(offer)

                        await ws.send(json.dumps({
                            "type": "offer",
                            "sdp": self.pc.localDescription.sdp,
                            "from": "pc"
                        }))

                        print("Sent offer")

                    continue

                # ---------------------
                # ANSWER
                # ---------------------
                if msg_type == "answer":
                    print("Received answer")

                    answer = RTCSessionDescription(
                        sdp=data["sdp"],
                        type="answer"
                    )
                    await self.pc.setRemoteDescription(answer)

                # ---------------------
                # ICE 
                # ---------------------
                elif msg_type == "ice":
                    print("Received ICE candidate")

                    ice = candidate_from_sdp(data["candidate"])
                    ice.sdpMid = data["sdpMid"]
                    ice.sdpMLineIndex = data["sdpMLineIndex"]

                    await self.pc.addIceCandidate(ice)

        # Clean up
        self.ws = None
        if self.pc:
            await self.pc.close()