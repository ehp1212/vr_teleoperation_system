import math

class RotationProcessor:
    def __init__(self):
        self.yaw = 0.0
        self.pitch = 0.0


    def process(self, q):
        ux, uy, uz, uw = q

        # --------------------
        # UNITY(Left) -> ROS2(Right) Coordinate Mapping
        # --------------------
        # Unity: X(Right), Y(Up), Z(Forward)
        # ROS2:  X(Forward), Y(Left), Z(Up)
        # ROS_x = Unity_z, ROS_y = -Unity_x, ROS_z = Unity_y
        qx = uz
        qy = ux
        qz = -uy
        qw = uw

        # --------------------
        # YAW (Z-axis rotation)
        # --------------------
        siny_cosp = 2.0 * (qw * qz + qx * qy)
        cosy_cosp = 1.0 - 2.0 * (qy * qy + qz * qz)
        yaw = math.atan2(siny_cosp, cosy_cosp)

        # --------------------
        # 3. PITCH (Y-axis rotation)
        # --------------------
        sinp = 2.0 * (qw * qy - qz * qx)
        if abs(sinp) >= 1:
            pitch = math.copysign(math.pi / 2, sinp)
        else:
            pitch = math.asin(sinp)


        self.yaw = yaw
        self.pitch = pitch

        return yaw, pitch