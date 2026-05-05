import math
import rclpy
from rclpy.node import Node
from tf2_ros import Buffer, TransformListener
from tf2_ros import LookupException, ConnectivityException, ExtrapolationException

class PoseReceiverNode(Node):
    def __init__(self, pose_shared_dict):
        super().__init__('pose_receiver_node')
        
        self.shared_pose = pose_shared_dict

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        
        self.timer = self.create_timer(0.1, self.timer_callback)

    def timer_callback(self):
        try:
            # map 프레임 기준 camera_link의 6-DoF 위치를 가져옴 (이미 ROS2 좌표계)
            trans = self.tf_buffer.lookup_transform('map', 'camera_link', rclpy.time.Time())
            
            # Translation (location: x, y, z)
            t = trans.transform.translation
            # Rotation (rotation: qx, qy, qz, qw)
            q = trans.transform.rotation
            
            # Update dict for recv data
            self.shared_pose.update({
                'stamp_sec': trans.header.stamp.sec,
                'stamp_nanosec': trans.header.stamp.nanosec,
                'frame_id': 'map',
                'child_frame_id': 'camera_link',
                'x': t.x, 'y': t.y, 'z': t.z,
                'qx': q.x, 'qy': q.y, 'qz': q.z, 'qw': q.w
            })
        except (LookupException, ConnectivityException, ExtrapolationException) as e:
            # might be called in early few frames
            # self.get_logger().warn(f"TF Lookup failed: {str(e)}") 
            pass