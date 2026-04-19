from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge


class ImageSubscriber(Node):
    def __init__(self, track, topic_name="/camera/image_raw"):
        super().__init__("image_subscriber")

        self.track = track
        self.bridge = CvBridge()

        self.subscription = self.create_subscription(
            Image,
            topic_name,
            self.callback,
            10
        )

        print(f"[ROS2] Subscribed to {topic_name}")

    def callback(self, msg):
        try:
            # ROS2 Image → OpenCV (numpy)
            frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")

            self.track.latest_frame = frame

        except Exception as e:
            print(f"[ROS2] Error: {e}")