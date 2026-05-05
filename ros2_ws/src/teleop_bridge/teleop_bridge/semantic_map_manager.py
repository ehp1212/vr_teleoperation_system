import time
import math
import json

from multiprocessing import Queue

# TODO: Sementic categorisation for frontier 
class SemanticMapManager:
    def __init__(self, queue: Queue, distance_threshold=0.5):
        """
        The Central Single Source of Truth for 3D Spatial Memory.
        ------------------------------
        Dictionary to store objects. 
        Format: { obj_id: {'class': str,
                  'x': float, 
                  'y': float, 
                  'z': float, 
                  'last_seen': float} }
        """

        self.spatial_memory = {}
        self.next_obj_id = 0
        self.distance_threshold = distance_threshold

        self.source_queue = queue
        
    def inject_pose_source(self, shared_pose):
        """
        Injected by orchestrator
        """
        self.pose_source = shared_pose

    def update_with_raw_detections(self, raw_objects):
        """
        Writer: Called every time the Perception Engine sends new data via Queue.
        Performs Clustering / Data Association.
        """
        if self.pose_source is None:
            return
            
        robot_x, robot_y, robot_yaw = self.pose_source.get()
        current_time = time.time()

        for new_obj in raw_objects:
            # 가정: 퍼셉션 엔진이 주는 raw_objects는 로봇 기준 '상대적 거리(local_x, local_y)'라고 가정
            # 만약 이미 global_xy를 준다면 이 계산은 퍼셉션 엔진 쪽으로 이동해야 합니다.
            local_x = new_obj.get('local_x', 0.0) 
            local_y = new_obj.get('local_y', 0.0)
            
            # [핵심] 로컬 좌표를 로봇의 현재 위치(x, y, yaw)를 이용해 글로벌 좌표로 변환
            new_x = robot_x + (local_x * math.cos(robot_yaw) - local_y * math.sin(robot_yaw))
            new_y = robot_y + (local_x * math.sin(robot_yaw) + local_y * math.cos(robot_yaw))
            
            new_cls = new_obj['class']
            
            # Step 1: Find if this object already exists in memory
            matched_id = None
            min_dist = float('inf')

            for obj_id, existing_obj in self.spatial_memory.items():
                if existing_obj['class'] == new_cls:
                    # Calculate Euclidean distance
                    dist = math.hypot(existing_obj['x'] - new_x, existing_obj['y'] - new_y)
                    if dist < self.distance_threshold and dist < min_dist:
                        min_dist = dist
                        matched_id = obj_id

            # Step 2: Update or Insert
            if matched_id is not None:
                # Update existing object (Simple Moving Average for smoothing)
                old_x = self.spatial_memory[matched_id]['x']
                old_y = self.spatial_memory[matched_id]['y']
                
                self.spatial_memory[matched_id]['x'] = (old_x + new_x) / 2.0
                self.spatial_memory[matched_id]['y'] = (old_y + new_y) / 2.0
                self.spatial_memory[matched_id]['last_seen'] = current_time
            else:
                # Insert new object
                new_obj_data = {
                    'class': new_cls,
                    'x': new_x,
                    'y': new_y,
                    'last_seen': current_time
                }

                self.spatial_memory[self.next_obj_id] = new_obj_data
                self.next_obj_id += 1

    # ---------------------------------------------------------
    # Readers (Getters for other systems)
    # ---------------------------------------------------------

    def get_obstacles_for_costmap(self):
        """
        Reader 1: Nav2 Costmap
        Returns a clean list of (x, y) coordinates for the ROS 2 Nav2 stack.
        """
        # Example: Filter out objects that haven't been seen in the last 60 seconds (Ghosts)
        current_time = time.time()
        active_obstacles = []
        for obj in self.spatial_memory.values():
            if current_time - obj['last_seen'] < 60.0: 
                active_obstacles.append((obj['x'], obj['y']))
        return active_obstacles

    def export_session_data(self):
        """
        Reader 2: Cloud / DB / Digital Twin
        Returns the entire map as a GeoJSON-like dictionary when the session ends.
        """
        features = []
        for obj_id, obj in self.spatial_memory.items():
            features.append({
                "id": obj_id,
                "class": obj['class'],
                "coordinates": [round(obj['x'], 2), round(obj['y'], 2)]
            })
            
        return {
            "session_end_time": time.time(),
            "total_objects_found": len(self.spatial_memory),
            "features": features
        }