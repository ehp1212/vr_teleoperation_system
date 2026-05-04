import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid
from nav2_msgs.action import NavigateToPose
from rclpy.action import ActionClient
import numpy as np
import cv2
import math

class SemanticFrontierExplorer(Node):
    def __init__(self, semantic_map_manager):
        super().__init__('semantic_frontier_explorer')
        
        # 1. 시스템 연결
        self.map_sub = self.create_subscription(OccupancyGrid, '/map', self.map_callback, 10)
        self.nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        
        # 진실의 방(3D Map) 접근 권한 획득
        self.map_manager = semantic_map_manager 
        
        # 탐색 목표 (예: 박스 주변을 우선적으로 탐색하고 싶다!)
        self.target_class_to_explore = "shelves" 

    def map_callback(self, msg):

        """SLAM 지도가 업데이트될 때마다 프론티어를 다시 계산합니다."""
        # 1. ROS 지도를 OpenCV 이미지 배열로 변환
        width = msg.info.width
        height = msg.info.height
        resolution = msg.info.resolution
        origin_x = msg.info.origin.position.x
        origin_y = msg.info.origin.position.y
        
        # 1D 배열을 2D 이미지로 변환
        grid = np.array(msg.data).reshape((height, width))
        
        # 2. OpenCV 마법: 프론티어(경계선) 찾기
        # Free Space (0) 영역 마스크 생성
        free_space = np.uint8(grid == 0) * 255
        # Unknown Space (-1) 영역 마스크 생성
        unknown_space = np.uint8(grid == -1) * 255
        
        # 빈 공간을 1픽셀 팽창(Dilate)시켜 미지 구역과 겹치게 만듦
        kernel = np.ones((3,3), np.uint8)
        dilated_free = cv2.dilate(free_space, kernel, iterations=1)
        
        # 팽창된 빈 공간과 미지 구역이 겹치는 곳이 바로 '프론티어'!
        frontiers_img = cv2.bitwise_and(dilated_free, unknown_space)
        
        # 3. 경계선들을 군집화(Clustering)하여 중심점 찾기
        contours, _ = cv2.findContours(frontiers_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        frontier_candidates = []
        for cnt in contours:
            # 경계선이 너무 작으면(노이즈) 무시
            if cv2.contourArea(cnt) > 5.0: 
                M = cv2.moments(cnt)
                if M["m00"] != 0:
                    cx_pixel = int(M["m10"] / M["m00"])
                    cy_pixel = int(M["m01"] / M["m00"])
                    
                    # 픽셀 좌표를 다시 실제 글로벌 좌표(m)로 변환
                    global_x = origin_x + (cx_pixel * resolution)
                    global_y = origin_y + (cy_pixel * resolution)
                    frontier_candidates.append((global_x, global_y))

        # 4. [핵심] 시맨틱 스코어링 로직 실행!
        best_frontier = self._select_best_frontier_semantically(frontier_candidates)
        
        # 5. Nav2로 명령 쏘기
        if best_frontier:
            self._send_nav_goal(best_frontier[0], best_frontier[1])


    def _select_best_frontier_semantically(self, frontiers):
        """단순히 가까운 곳이 아니라, '기억'을 바탕으로 가장 가치 있는 곳을 고릅니다."""
        if not frontiers:
            return None

        # 현재 맵에 있는 객체들 가져오기
        known_objects = self.map_manager.get_clean_map()
        
        best_frontier = None
        highest_score = -float('inf')

        for fx, fy in frontiers:
            score = 0
            
            # (기본 점수) 거리 계산: 로봇과 가까울수록 좋음 (현재 로봇 위치가 필요함)
            # dist_to_robot = math.hypot(robot_x - fx, robot_y - fy)
            # score -= dist_to_robot * 1.0  
            
            # (시맨틱 보너스 점수) 타겟 객체와의 거리
            for obj in known_objects:
                if obj['class'] == self.target_class_to_explore:
                    dist_to_obj = math.hypot(obj['x'] - fx, obj['y'] - fy)
                    
                    # 만약 프론티어가 내가 찾던 박스 반경 3m 이내에 있다면 엄청난 보너스 점수 부여!
                    # "저기 박스가 있었지? 그 주변 구석탱이에 박스가 더 있을지도 몰라! 거길 파보자!"
                    if dist_to_obj < 3.0:
                        score += 500.0  

            if score > highest_score:
                highest_score = score
                best_frontier = (fx, fy)

        return best_frontier

    def _send_nav_goal(self, x, y):
        """Nav2 Action Server에 목적지 하달"""
        goal_msg = NavigateToPose.Goal()
        goal_msg.pose.header.frame_id = 'map'
        goal_msg.pose.pose.position.x = float(x)
        goal_msg.pose.pose.position.y = float(y)
        goal_msg.pose.pose.orientation.w = 1.0 # 일단 해당 방향 그대로 정지
        
        # 이미 주행 중이 아닐 때만 쏜다 (상태 관리 로직 추가 필요)
        self.nav_client.send_goal_async(goal_msg)
        print(f"[Commander] Ordered Nav2 to explore Semantic Frontier at X:{x:.2f}, Y:{y:.2f}")