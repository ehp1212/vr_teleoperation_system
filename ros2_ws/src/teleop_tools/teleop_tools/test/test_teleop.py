import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import sys, select, termios, tty

# 키보드 입력 설정
msg = """
---------------------------
Isaac Sim 로봇 제어 테스트
---------------------------
움직임 제어:
    w : 전진 (Throttle +)
    s : 후진 (Throttle -)
    a : 좌회전 (Steering +)
    d : 우회전 (Steering -)

    space : 정지 (모두 0)

CTRL-C 문자를 누르면 종료합니다.
"""

moveBindings = {
    'w': (1.0, 0.0),
    's': (-1.0, 0.0),
    'a': (0.0, 1.0),
    'd': (0.0, -1.0),
}

def getKey(settings):
    tty.setraw(sys.stdin.fileno())
    select.select([sys.stdin], [], [], 0.1)
    key = sys.stdin.read(1)
    termios.tcsetattr(sys.stdin, sys.stdin.fileno(), settings)
    return key

class TestTeleopNode(Node):
    def __init__(self):
        super().__init__('test_teleop_publisher')
        # 사용자가 지정한 토픽 이름으로 퍼블리셔 생성
        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel_target', 10)
        
        self.speed = 0.5    # 선속도 배율
        self.turn = 0.5     # 조향각 배율
        self.get_logger().info("키보드 제어 노드가 시작되었습니다.")

    def run(self):
        settings = termios.tcgetattr(sys.stdin)
        x = 0.0
        th = 0.0
        try:
            print(msg)
            while True:
                key = getKey(settings)
                if key in moveBindings.keys():
                    x = moveBindings[key][0] * self.speed
                    th = moveBindings[key][1] * self.turn
                elif key == ' ':
                    x = 0.0
                    th = 0.0
                else:
                    if (key == '\x03'): # CTRL-C
                        break
                
                twist = Twist()
                twist.linear.x = float(x)
                twist.angular.z = float(th)
                self.pub_cmd.publish(twist)
                
                print(f"\r현재 출력 -> Throttle: {x:.2f}, Steering: {th:.2f}  ", end="")

        except Exception as e:
            print(e)
        finally:
            twist = Twist()
            twist.linear.x = 0.0
            twist.angular.z = 0.0
            self.pub_cmd.publish(twist)
            termios.tcsetattr(sys.stdin, sys.stdin.fileno(), settings)

def main(args=None):
    rclpy.init(args=args)
    node = TestTeleopNode()
    node.run()
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()