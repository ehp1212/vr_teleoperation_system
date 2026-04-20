import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Pose
import socket
import json


class UDPPoseNode(Node):
    def __init__(self):
        super().__init__('udp_pose_node')

        self.publisher = self.create_publisher(Pose, '/ee_target_pose', 10)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", 5005))
        self.sock.setblocking(False)

        self.get_logger().info("UDP Pose Node Started")

    def update(self):
        try:
            data, _ = self.sock.recvfrom(1024)
            msg = json.loads(data.decode())

            pose = Pose()

            # TODO: set debug position  for now
            pose.position.x = 0.4
            pose.position.y = 0.0
            pose.position.z = 0.5

            # pose.position.x = msg["px"]
            # pose.position.y = msg["pz"]
            # pose.position.z = -msg["py"]

            # rotation (Unity → ROS)
            pose.orientation.x = msg["rx"]
            pose.orientation.y = msg["rz"]
            pose.orientation.z = -msg["ry"]
            pose.orientation.w = msg["rw"]

            self.publisher.publish(pose)

        except BlockingIOError:
            pass
        except Exception as e:
            self.get_logger().warn(f"UDP error: {e}")