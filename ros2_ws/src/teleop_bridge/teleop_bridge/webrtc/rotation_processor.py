import math

class RotationProcessor:
    def __init__(self):
        self.yaw = 0.0
        self.pitch = 0.0


    def process(self, q):
        x,y,z,w = q

        # --------------------
        # UNITY -> ROS2
        # --------------------
        qx = z
        qy = -x
        qz = y
        qw = w

        # --------------------
        # YAW, Pitch
        # --------------------
        siny_cosp = 2.0 * (qw * qz + qx * qy)
        cosy_cosp = 1.0 - 2.0 * (qy * qy + qz * qz)
        yaw = math.atan2(siny_cosp, cosy_cosp)

        sinp = 2.0 * (qw * qy - qz * qx)
        if abs(sinp) >= 1:
            pitch = math.copysign(math.pi / 2, sinp)
        else:
            pitch = math.asin(sinp)

        self.yaw = yaw
        self.pitch = pitch

        return yaw, pitch        