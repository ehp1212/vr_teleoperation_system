from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from rclpy.qos import QoSProfile
from rclpy.qos import QoSReliabilityPolicy
from rclpy.qos import QoSHistoryPolicy

from teleop_bridge.utils.logger import logger
import time

class ImageSubscriber(Node):
    def __init__(self, track, topic_name="/camera/image_raw"):
        super().__init__("image_subscriber")

        self.track = track
        self.bridge = CvBridge()

        qos = QoSProfile(
                    reliability=QoSReliabilityPolicy.BEST_EFFORT,
                    history=QoSHistoryPolicy.KEEP_LAST,
                    depth=1
                )

        self.subscription = self.create_subscription(
            Image,
            topic_name,
            self.callback,
            qos
        )

        self.frame_id = 0
        print(f"[ROS2] Subscribed to {topic_name}")

    def callback(self, msg):
        self.frame_id += 1
        ts = time.time()
        logger.log("capture", self.frame_id, ts, extra={"stream": "rgb"})

        try:
            # ROS2 Image → OpenCV (numpy)
            rgb = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")

            self.track.update(rgb, ts, self.frame_id)

        except Exception as e:
            print(f"[ROS2] Error: {e}")
