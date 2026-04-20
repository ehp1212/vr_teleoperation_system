import asyncio
import json
import websockets
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack

class WebRTCClient:
    def __init__(self, isaac_image_track, hw_image_track):
        self.pc = RTCPeerConnection()
        self.signaling_url = "ws://127.0.0.1:8765"

        self.isaac_image_track = isaac_image_track
        self.hw_image_track = hw_image_track

        # Add tracks
        self.pc.addTransceiver("video", direction="sendonly")

        self.pc.addTrack(self.isaac_image_track)
        # self.pc.addTrack(self.hw_image_track)

        # ICE
        @self.pc.on("icecandidate")
        async def on_icecandidate(candidate):
            if candidate is not None and hasattr(self, "ws"):
                msg = {
                    "type": "candidate",
                    "candidate": candidate.to_sdp(),
                    "sdpMid": candidate.sdpMid,
                    "sdpMLineIndex": candidate.sdpMLineIndex,
                }
                await self.ws.send(json.dumps(msg))
        
        @self.pc.on("connectionstatechange")
        async def on_state_change():
            print("Connection state:", self.pc.connectionState)


        print(f"WebRTC node initialized : {self.signaling_url}")

    async def connect_signaling(self):
        async with websockets.connect(self.signaling_url) as ws:
            self.ws = ws
            print(f"Connected to signaling server: {self.signaling_url}")

            # =====================
            # Offer
            # =====================
            offer = await self.pc.createOffer()
            await self.pc.setLocalDescription(offer)
            
            await asyncio.sleep(1)
            print(self.pc.localDescription.sdp)

            message = {
                "type": "offer",
                "sdp": self.pc.localDescription.sdp,
            }
            await ws.send(json.dumps(message))
            print("Sent offer")


            # =====================
            # Receive
            # =====================
            async for raw_msg in ws:
                data = json.loads(raw_msg)
                msg_type = data.get("type")

                if msg_type == "answer":
                    answer = RTCSessionDescription(
                        sdp=data["sdp"],
                        type="answer",
                    )
                    await self.pc.setRemoteDescription(answer)

                elif msg_type == "candidate":
                    print("Received ICE candidate message")
                    candidate = data["candidate"]

                    from aiortc.sdp import candidate_from_sdp

                    ice_candidate = candidate_from_sdp(candidate)
                    ice_candidate.sdpMid = data["sdpMid"]
                    ice_candidate.sdpMLineIndex = data["sdpMLineIndex"]

                    await self.pc.addIceCandidate(ice_candidate)