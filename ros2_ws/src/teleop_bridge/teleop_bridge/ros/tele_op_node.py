import json
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from geometry_msgs.msg import Vector3

from teleop_bridge.webrtc.rotation_processor import RotationProcessor
from teleop_bridge.webrtc.control_processor import ControlProcessor

import time
from teleop_bridge.utils.logger import logger

class TeleopNode(Node):
    def __init__(self):
        super().__init__('teleop_node')

        # ---------------------------
        # Publishers
        # ---------------------------
        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel_target', 10)
        self.pub_pose = self.create_publisher(Vector3, '/cmd_pose', 10)

        # ---------------------------
        # Processor
        # ---------------------------
        self.rotation_processor = RotationProcessor()
        self.control_processor = ControlProcessor()

    # =====================
    # Handle incoming data
    # =====================
    def handle_message(self, data, control_id):
        # ---------------------------
        # Rotation
        # ---------------------------
        q = (
            data["rotation"]["x"],
            data["rotation"]["y"],
            data["rotation"]["z"],
            data["rotation"]["w"]
        )

        yaw, pitch = self.rotation_processor.process(q)

        # ---------------------------
        # Control
        # ---------------------------
        control = (
            data["control"]["x"],
            data["control"]["y"]
        )
        
        steering, throttle = self.control_processor.process(control)

        # ---------------------------
        # Publish
        # ---------------------------
        self.publish_cmd(steering, throttle)
        self.publish_pose(yaw, pitch)

    # =====================
    # Publish control
    # =====================
    def publish_cmd(self, steering, throttle):
        msg = Twist()

        msg.linear.x = throttle
        msg.angular.z = steering

        self.pub_cmd.publish(msg)

    # =====================
    # Publish rotation
    # =====================
    def publish_pose(self, yaw, pitch):
        msg = Vector3()

        msg.x = yaw
        msg.y = pitch
        msg.z = 0.0
        
        self.pub_pose.publish(msg)