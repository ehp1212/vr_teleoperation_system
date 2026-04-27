import asyncio
import json
import websockets

from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer
from aiortc.sdp import candidate_from_sdp

from .rotation_processor import RotationProcessor
from .control_processor import ControlProcessor

import time
from teleop_bridge.utils.logger import logger


def log(tag, *args):
    print(f"[{time.time():.3f}][{tag}]", *args)

class WebRTCClient:
    def __init__(self, teleop_node, isaac_image_track, isaac_depth_track):
        self.signaling_url = "ws://172.20.10.8:8765"

        self.teleop_node = teleop_node
        self.isaac_image_track = isaac_image_track
        self.isaac_depth_track = isaac_depth_track

        self.pc = None
        self.ws = None

        self.rotation_processor = RotationProcessor()
        self.control_processor = ControlProcessor()

        self.connected = False

        print(f"WebRTC client initialized: {self.signaling_url}")

    # =====================
    # Connect Loop
    # =====================
    async def connect_loop(self):
        while True:
            if not self.connected:
                try:
                    print("Connecting to signaling...")
                    await self.connect_signaling()

                except Exception as e:
                    print("Connection error:", e)

            await asyncio.sleep(1)

    # =====================
    # Signaling
    # =====================
    async def connect_signaling(self):
        config = RTCConfiguration(
            iceServers=[
                RTCIceServer(urls=["stun:stun.l.google.com:19302"])
            ]
        )

        self.pc = RTCPeerConnection(configuration=config)

        # =====================
        # ICE candidate 
        # =====================
        @self.pc.on("icecandidate")
        async def on_icecandidate(candidate):
            print("[ICE SEND]", candidate)
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
            state = self.pc.connectionState
            log("PC", self.pc.connectionState)
            
            if state == "connected":
                self.connected = True                

            if self.pc.connectionState in ["failed", "closed"]:
                self.connected = False

        # control channel (unity -> ros2)
        control_channel = self.pc.createDataChannel(
            "control",
            ordered=False,
            maxRetransmits=0
        )

        @control_channel.on("open")
        def on_open():
            print(f"[DATACHANNEL] Control - open")

        @control_channel.on("message")
        def on_message(message):
            recv_ts = time.time()
            data = json.loads(message)
            
            control_id = data.get("control_id", -1)
            logger.log(
                "control_recv",
                control_id,
                recv_ts,
                extra={"stream": "control"}
            )

            self.teleop_node.handle_message(data, control_id)
            
        @control_channel.on("close")
        def on_close():
            print(f"[DATACHANNEL] Control - close")

        # Track 
        self.pc.addTrack(self.isaac_image_track)
        self.pc.addTrack(self.isaac_depth_track)

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

                        while self.pc.iceGatheringState != "complete":
                            await asyncio.sleep(0.1)

                        print("ICE gathering state:", self.pc.iceGatheringState)

                        sdp = self.pc.localDescription.sdp
                        print("SDP has candidate:", "a=candidate" in sdp)

                        for line in sdp.splitlines():
                            if line.startswith("a=candidate"):
                                print("[SDP CANDIDATE]", line)

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

                    candidate_sdp = data.get("candidate")
                    if not candidate_sdp:
                        print("[ICE] empty candidate")
                        continue

                    ice = candidate_from_sdp(candidate_sdp)

                    ice.sdpMid = data.get("sdpMid")
                    ice.sdpMLineIndex = data.get("sdpMLineIndex", 0)

                    try:
                        await self.pc.addIceCandidate(ice)
                    except Exception as e:
                        print("[ICE] addIceCandidate failed:", e)

                    print("[ICE] mid:", ice.sdpMid, "index:", ice.sdpMLineIndex)

        # Clean up
        self.ws = None
        if self.pc:
            await self.pc.close()