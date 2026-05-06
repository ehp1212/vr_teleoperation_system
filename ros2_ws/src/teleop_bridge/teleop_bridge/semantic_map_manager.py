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

        self.on_new_object_callback = None

    def set_new_object_callback(self, callback):
        """
        Setter method to attach WebRTC send function
        """
        self.on_new_object_callback = callback

    def update_with_raw_detections(self, raw_objects):
        """
        Writer: Called every time the Perception Engine sends new data via Queue.
        Performs Clustering / Data Association using pre-calculated global coordinates.
        """
        current_time = time.time()

        for new_obj in raw_objects:
            # 1. Extract the already-converted global coordinates from perception metadata
            new_x = new_obj.get('x', 0.0)
            new_y = new_obj.get('y', 0.0)
            new_z = new_obj.get('z', 0.0)
            new_cls = new_obj.get('class', 'unknown')
            
            # Step 1: Find if this object already exists in memory
            matched_id = None
            min_dist = float('inf')

            for obj_id, existing_obj in self.spatial_memory.items():
                if existing_obj['class'] == new_cls:
                    # Calculate 2D Euclidean distance (can be changed to 3D if needed)
                    dist = math.hypot(existing_obj['x'] - new_x, existing_obj['y'] - new_y)
                    if dist < self.distance_threshold and dist < min_dist:
                        min_dist = dist
                        matched_id = obj_id

            # Step 2: Update or Insert
            if matched_id is not None:
                # Update existing object (Smoothing with moving average to reduce jitter)
                alpha = 0.7  # 70% old value, 30% new value
                
                self.spatial_memory[matched_id]['x'] = self.spatial_memory[matched_id]['x'] * alpha + new_x * (1 - alpha)
                self.spatial_memory[matched_id]['y'] = self.spatial_memory[matched_id]['y'] * alpha + new_y * (1 - alpha)
                self.spatial_memory[matched_id]['z'] = self.spatial_memory[matched_id].get('z', 0.0) * alpha + new_z * (1 - alpha)
                self.spatial_memory[matched_id]['last_seen'] = current_time
            else:
                # Insert new object
                new_obj_data = {
                    'class': new_cls,
                    'x': new_x,
                    'y': new_y,
                    'z': new_z,
                    'last_seen': current_time
                }
                self.spatial_memory[self.next_obj_id] = new_obj_data
                self.next_obj_id += 1

                # send data to channel
                self.on_new_object_callback(new_obj_data)

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
    
def map_manager_worker(manager: SemanticMapManager):
    print("[MapManager] Worker thread started.")
    while True:
        try:
            raw_detections = manager.source_queue.get()
            
            if raw_detections is None:
                break
                
            # 맵 업데이트 실행
            manager.update_with_raw_detections(raw_detections)
            
        except Exception as e:
            print(f"[MapManager] Error: {e}")