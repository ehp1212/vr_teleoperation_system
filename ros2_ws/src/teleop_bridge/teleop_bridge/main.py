import asyncio
import rclpy

from teleop_bridge.webrtc_client import WebRTCClient
from teleop_bridge.image_subscriber import ImageSubscriber
from teleop_bridge.video_track import SimpleVideoTrack


async def async_main():
    rclpy.init()

    # =====================
    # Track 
    # =====================
    isaac_track = SimpleVideoTrack("ISAAC")
    hw_track = SimpleVideoTrack("HARDWARE")

    # =====================
    # ROS2 Node
    # =====================
    isaac_node = ImageSubscriber(isaac_track, "/camera/image_raw")
    # hw_node = ImageSubscriber(hw_track, "/hw/image")  # 나중에

    # =====================
    # WebRTC Client
    # =====================
    client = WebRTCClient(isaac_track, hw_track)

    # =====================
    # ROS spin (async)
    # =====================
    async def ros_spin():
        while rclpy.ok():
            rclpy.spin_once(isaac_node, timeout_sec=0.01)
            await asyncio.sleep(0.01)

    # =====================
    # Execute
    # =====================
    await asyncio.gather(
        client.connect_signaling(),
        ros_spin()
    )


def main():
    asyncio.run(async_main())