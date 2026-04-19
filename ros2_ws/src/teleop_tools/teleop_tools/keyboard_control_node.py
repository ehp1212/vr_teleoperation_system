import os
import sys
import select
import time
import rclpy
from geometry_msgs.msg import Twist

if os.name != 'nt':
    import termios
    import tty

# --- 파라미터 ---
SPEED = 0.3
TURN = 1.0
HOLD_TIMEOUT = 0.15  # 🔥 이 시간동안 입력 없으면 0으로

def get_key(settings):
    tty.setcbreak(sys.stdin.fileno())
    rlist, _, _ = select.select([sys.stdin], [], [], 0.02)
    key = sys.stdin.read(1) if rlist else ''
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    return key

def main():
    settings = termios.tcgetattr(sys.stdin)

    rclpy.init()
    node = rclpy.create_node('keyboard_deadman_real')
    pub = node.create_publisher(Twist, '/cmd_vel', 10)

    last_time = time.time()
    last_linear = 0.0
    last_angular = 0.0

    print("""
REAL Deadman Control
-------------------
Hold key to move
Release → immediate stop
W/S: forward/back
A/D: steering
CTRL-C to quit
""")

    try:
        while rclpy.ok():
            key = get_key(settings)
            now = time.time()

            # --- 키 입력 처리 ---
            if key != '':
                last_time = now

                if key == 'w':
                    last_linear = SPEED
                elif key == 's':
                    last_linear = -SPEED
                elif key == 'a':
                    last_angular = TURN
                elif key == 'd':
                    last_angular = -TURN

                print(f"KEY: {key}")

            # --- deadman ---
            if now - last_time > HOLD_TIMEOUT:
                last_linear = 0.0
                last_angular = 0.0

            # publish
            msg = Twist()
            msg.linear.x = last_linear
            msg.angular.z = last_angular
            pub.publish(msg)

    except KeyboardInterrupt:
        pass

    finally:
        pub.publish(Twist())
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)

if __name__ == '__main__':
    main()