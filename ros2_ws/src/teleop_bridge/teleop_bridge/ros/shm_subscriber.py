import time
import numpy as np
import cv2
import rclpy

from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from multiprocessing import shared_memory

from teleop_bridge.utils.logger import logger


class ShmImageSubscriber(Node):
    def __init__(self, name, topic_name, shm_name, shape, mp_event):
        super().__init__(f"{name}_subscriber")
        self.name = name
        self.bridge = CvBridge()
        self.mp_event = mp_event
        self.shape = shape

        # Conect to shared memory
        self.shm = shared_memory.SharedMemory(name=shm_name)
        self.shared_array = np.ndarray(self.shape, dtype=np.uint8, buffer=self.shm.buf)

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

    def callback(self, msg):
        try:
            self.frame_id += 1
            ts = time.time()

            # Capture img
            logger.log("capture", self.frame_id, ts, extra={"stream": f"{self.name}"})

            # ROS2 -> OpenCV 
            img = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")

            # ------------------------------
            # image processing for ROI
            # ------------------------------
            h, w = img.shape[:2]

            # blur
            blurred_img = cv2.GaussianBlur(img, (31, 31), 0)

            # ROI region
            roi_ratio = 0.8
            roi_w, roi_h = int(w * roi_ratio), int(h * roi_ratio)
            x1 = (w - roi_w) // 2
            y1 = (h - roi_h) // 2
            x2 = x1 + roi_w
            y2 = y1 + roi_h

            # combined filtered and roi 
            blurred_img[y1:y2, x1:x2] = img[y1:y2, x1:x2]
            img = blurred_img

            # Copy to memory
            self.shared_array[:] = img

            # Invoke event
            self.mp_event.set()

        except Exception as e:
            print(f"[ROS2] {self.name} Error: {e}")

class ShmDepthSubscriber(Node):
    def __init__(self, name, topic_name, shm_name, shape, mp_event):
        super().__init__(f"{name}_subscriber")
        self.name = name
        self.bridge = CvBridge()
        self.mp_event = mp_event
        self.shape = shape

        # Conect to shared memory
        self.shm = shared_memory.SharedMemory(name=shm_name)
        self.shared_array = np.ndarray(self.shape, dtype=np.uint8, buffer=self.shm.buf)

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


    def callback(self, msg):
        try:
            self.frame_id += 1
            ts = time.time()

            # Capture img
            logger.log("capture", self.frame_id, ts, extra={"stream": f"{self.name}"})

            depth = self.bridge.imgmsg_to_cv2(msg, desired_encoding="32FC1")
            depth_norm = np.clip(depth / 5.0, 0, 1)
            img = (depth_norm * 255).astype(np.uint8)
            img = cv2.resize(img, (self.shape[1], self.shape[0])) # (width, height)
            
            # ------------------------------
            # image processing for ROI
            # ------------------------------
            h, w = img.shape

            # blur
            blurred_img = cv2.GaussianBlur(img, (31, 31), 0)

            # ROI region
            roi_w, roi_h = int(w * 0.5), int(h * 0.5)
            x1 = (w - roi_w) // 2
            y1 = (h - roi_h) // 2
            x2 = x1 + roi_w
            y2 = y1 + roi_h

            # combined filtered and roi 
            blurred_img[y1:y2, x1:x2] = img[y1:y2, x1:x2]
            img = blurred_img

            # update 
            self.shared_array[:] = img

            # Invoke event
            self.mp_event.set()

        except Exception as e:
            print(f"[ROS2] {self.name} Error: {e}")

def ros_worker_process(node_class, args):
    rclpy.init()
    node = node_class(*args)
    try:
        rclpy.spin(node)
    finally:
        node.shm.close()
        node.destroy_node()
        rclpy.shutdown()