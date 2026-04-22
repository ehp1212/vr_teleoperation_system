import asyncio
import rclpy
import threading

from .webrtc.webrtc_client import WebRTCClient
from .ros.image_subscriber import ImageSubscriber
from .webrtc.video_track import SimpleVideoTrack


# =====================
# ROS spin (thread)
# =====================
def ros_spin(node):
    while rclpy.ok():
        rclpy.spin_once(node, timeout_sec=0.01)


# =====================
# Async main
# =====================
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
    # hw_node = ImageSubscriber(hw_track, "/hw/image")

    # =====================
    # ROS thread
    # =====================
    ros_thread = threading.Thread(
        target=ros_spin,
        args=(isaac_node,),  
        daemon=True
    )
    ros_thread.start()

    # =====================
    # WebRTC Client
    # =====================
    client = WebRTCClient(isaac_track, hw_track)

    # =====================
    # Execute (reconnect loop inside client)
    # =====================
    await client.connect_loop()


# =====================
# Entry point
# =====================
def main():
    asyncio.run(async_main())


if __name__ == "__main__":
    main()