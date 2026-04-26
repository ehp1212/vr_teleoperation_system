from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

import numpy as np
import time
from teleop_bridge.utils.logger import logger

class DepthSubscriber(Node):
    def __init__(self, depth_track, topic_name="/camera/depth/image_raw"):
        super().__init__("depth_subscriber")

        self.depth_track = depth_track
        self.bridge = CvBridge()

        self.subscription = self.create_subscription(
            Image,
            topic_name,
            self.callback,
            10
        )

        self.frame_id = 0
        print(f"[ROS2] Subscribed to {topic_name}")


    def callback(self, msg):
        self.frame_id += 1
        ts = time.time()
        logger.log("depth_capture", self.frame_id, ts)

        try:
            depth = self.bridge.imgmsg_to_cv2(msg, desired_encoding="32FC1")
            self.depth_track.update(depth, ts, self.frame_id)
        except Exception as e:
            print(f"[ROS2] Error: {e}")

