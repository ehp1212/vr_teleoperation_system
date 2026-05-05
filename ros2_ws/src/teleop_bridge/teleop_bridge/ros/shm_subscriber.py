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
    def __init__(self, name, topic_name, shm_name, shape, dtype, perc_event):
        super().__init__(f"{name}_subscriber")
        self.name = name
        self.bridge = CvBridge()
        self.perc_event = perc_event
        self.shape = shape
        self.dtype = np.dtype(dtype)

        # Conect to shared memory
        self.shm = shared_memory.SharedMemory(name=shm_name)
        self.shared_array = np.ndarray(
            self.shape,
            dtype=self.dtype,
            buffer=self.shm.buf
        )

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
        raise NotImplementedError("callback meethod not implemented")

        
class RgbVideoCallback(ShmImageSubscriber):
    def callback(self, msg):
        try:
            self.frame_id += 1
            ts = time.time()

            # Capture img
            logger.log("capture", self.frame_id, ts, extra={"stream": f"{self.name}"})

            # ROS2 -> OpenCV 
            img = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")

            # Copy to memory
            self.shared_array[:] = img

            # Invoke event
            self.perc_event.set()

        except Exception as e:
            print(f"[ROS2] {self.name} Error: {e}")

class DepthVideoCallback(ShmImageSubscriber):
    def callback(self, msg):
        try:
            self.frame_id += 1
            ts = time.time()
            logger.log("capture", self.frame_id, ts, extra={"stream": f"{self.name}"})

            depth = self.bridge.imgmsg_to_cv2(msg, desired_encoding="32FC1")

            if depth.shape != self.shape:
                depth = cv2.resize(
                    depth,
                    (self.shape[1], self.shape[0]),
                    interpolation=cv2.INTER_NEAREST
                )

            self.shared_array[:] = depth.astype(np.float32, copy=False)
            self.perc_event.set()

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