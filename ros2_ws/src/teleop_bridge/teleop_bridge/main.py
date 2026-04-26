import asyncio
import rclpy
import threading
from rclpy.executors import MultiThreadedExecutor

from .webrtc.webrtc_client import WebRTCClient
from .ros.image_subscriber import ImageSubscriber
from .ros.depth_subscriber import DepthSubscriber
from .ros.tele_op_node import TeleopNode

from .webrtc.video_track import SimpleVideoTrack
from .webrtc.depth_track import DepthVideoTrack

from teleop_bridge.utils.logger import logger

# =====================
# ROS spin (thread)
# =====================
def ros_spin(nodes):
    executor = MultiThreadedExecutor()

    for node in nodes:
        executor.add_node(node)

    try:
        executor.spin()
    finally:
        for node in nodes:
            node.destroy_node()


# =====================
# Async main
# =====================
async def async_main():
    rclpy.init()

    # =====================
    # Track
    # =====================
    isaac_rgb_track = SimpleVideoTrack("rgb")
    issac_depth_track = DepthVideoTrack("depth")

    hw_track = SimpleVideoTrack("HARDWARE")

    # =====================
    # ROS2 Node
    # =====================
    isaac_image_node = ImageSubscriber(isaac_rgb_track, "/camera/rgb/image_raw")
    isaac_depth_node = DepthSubscriber(issac_depth_track, "/camera/depth/image_raw")

    # hw_node = ImageSubscriber(hw_track, "/hw/image")

    teleop_node = TeleopNode()

    # =====================
    # ROS thread
    # =====================
    ros_thread = threading.Thread(
        target=ros_spin,
        args=([isaac_image_node, isaac_depth_node, teleop_node],),
        daemon=True
    )
    ros_thread.start()

    # =====================
    # WebRTC Client
    # =====================
    client = WebRTCClient(teleop_node, isaac_rgb_track, issac_depth_track, hw_track)

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
    # logger.log("program_start")
    main()
    # logger.log("program_end")