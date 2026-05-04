import time
import math
import json

# TODO: Sementic categorisation for frontier 
class SemanticMapManager:
    def __init__(self, distance_threshold=0.5):
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
        
        # Threshold (in meters) to consider a detection as an "existing" object
        self.distance_threshold = distance_threshold

    def update_with_raw_detections(self, raw_objects):
        """
        Writer: Called every time the Perception Engine sends new data via Queue.
        Performs Clustering / Data Association.
        """
        current_time = time.time()

        for new_obj in raw_objects:
            new_x, new_y = new_obj['global_xy']
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
                self.spatial_memory[self.next_obj_id] = {
                    'class': new_cls,
                    'x': new_x,
                    'y': new_y,
                    'last_seen': current_time
                }
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