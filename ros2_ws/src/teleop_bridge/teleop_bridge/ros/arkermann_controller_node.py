import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

class AckermannControllerNode(Node):
    def __init__(self):
        super().__init__('ackermann_controller')

        # Target 
        self.target_speed = 0.0
        self.target_steering = 0.0

        # Current state
        self.current_speed = 0.0

        # P gain
        self.kp_speed = 1.5

        # Publisher
        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel', 10)

        # Subscriber
        self.sub_target = self.create_subscription(
            Twist,
            '/cmd_vel_target',
            self.target_callback,
            10
        )

        self.sub_odom = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            10
        )

        # Timer (control loop)
        self.timer = self.create_timer(0.02, self.control_loop)  # 50Hz

    # =====================
    # Target callback
    # =====================
    def target_callback(self, msg):
        self.target_speed = msg.linear.x
        self.target_steering = msg.angular.z

    # =====================
    # Odom callback
    # =====================
    def odom_callback(self, msg):
        self.current_speed = msg.twist.twist.linear.x

    # =====================
    # Control loop
    # =====================
    def control_loop(self):
        # ---------------------------
        # Speed error
        # ---------------------------
        error = self.target_speed - self.current_speed

        # ---------------------------
        # P control
        # ---------------------------
        control_speed = self.target_speed + self.kp_speed * error

        # ---------------------------
        # Publish cmd_vel
        # ---------------------------
        cmd = Twist()

        cmd.linear.x = control_speed
        cmd.angular.z = self.target_steering  # steering은 그대로

        self.pub_cmd.publish(cmd)

        self.get_logger().info(
            f"target={self.target_speed:.2f}, current={self.current_speed:.2f}, cmd={control_speed:.2f}"
        )