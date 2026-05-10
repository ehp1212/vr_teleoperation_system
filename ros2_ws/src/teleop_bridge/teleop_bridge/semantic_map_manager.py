import time
import math
import json
import numpy as np  # Required for Kalman Filter matrix operations

from multiprocessing import Queue

# ==========================================
# 3D Kalman Filter for Stationary Objects
# ==========================================
class KalmanFilter3D:
    def __init__(self, init_x, init_y, init_z):
        """
        Initializes the Kalman Filter for a 3D point.
        """
        # 1. State vector [x, y, z]
        self.x = np.array([[init_x], 
                           [init_y], 
                           [init_z]], dtype=np.float32)
        
        # 2. Estimate Uncertainty (Covariance Matrix P)
        self.P = np.eye(3, dtype=np.float32) * 1.0
        
        # 3. Process Noise (Q) 
        # Assumes the object (e.g. vase, chair) is stationary. Set very small.
        self.Q = np.eye(3, dtype=np.float32) * 0.01
        
        # 4. Measurement Noise (R)
        # Represents the inaccuracy of YOLO + Depth sensor. 
        # Increase this if the sensor jitters a lot.
        self.R = np.eye(3, dtype=np.float32) * 0.25 

    def predict(self):
        """
        Predict step: Updates the estimate uncertainty based on process noise.
        """
        # Since it's a stationary object, state x remains the same.
        self.P = self.P + self.Q

    def update(self, meas_x, meas_y, meas_z):
        """
        Update step: Fuses the new sensor measurement with the predicted state.
        Returns the filtered (x, y, z) coordinates.
        """
        z = np.array([[meas_x], 
                      [meas_y], 
                      [meas_z]], dtype=np.float32)
        
        H = np.eye(3, dtype=np.float32)
        
        # Calculate Kalman Gain: K = P * H^T * (H * P * H^T + R)^-1
        S = H @ self.P @ H.T + self.R
        K = self.P @ H.T @ np.linalg.inv(S)
        
        # Update State: x = x + K * (z - H * x)
        self.x = self.x + K @ (z - H @ self.x)
        
        # Update Covariance: P = (I - K * H) * P
        self.P = (np.eye(3, dtype=np.float32) - K @ H) @ self.P
        
        return float(self.x[0, 0]), float(self.x[1, 0]), float(self.x[2, 0])


# ==========================================
# Semantic Map Manager
# ==========================================
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
                           'last_seen': float,
                           'belief': int,
                           'is_confirmed': bool,
                           'kf': KalmanFilter3D} }
        """
        self.source_queue = queue
        self.spatial_memory = {}
        self.next_obj_id = 0

        self.distance_threshold = distance_threshold
        
        # Belief system parameters
        self.belief_increment = 15  # increment point per detection
        self.belief_decay_rate = 10 # decrement point per frame
        self.confirm_threshold = 60 # confirm threshold point
        self.max_belief = 100       # max point

        self.stale_timeout = 3.0    # timeout (Fixed typo from state_timeout)

        self.on_new_object_callback = None

    def set_new_object_callback(self, callback):
        """
        Setter method to attach WebRTC or System send function
        """
        self.on_new_object_callback = callback

    def update_with_raw_detections(self, raw_objects):
        """
        Writer: Called every time the Perception Engine sends new data via Queue.
        Performs Data Association and Kalman Filtering.
        """
        current_time = time.time()

        # 1. Clean up old/ghost objects first
        self.cleanup_stale_objects(current_time)

        for new_obj in raw_objects:
            new_x = new_obj.get('x', 0.0)
            new_y = new_obj.get('y', 0.0)
            new_z = new_obj.get('z', 0.0)
            new_cls = new_obj.get('class', 'unknown')
            
            # Step 1: Data Association (Find matching existing object)
            matched_id = None
            min_dist = float('inf')

            for obj_id, existing_obj in self.spatial_memory.items():
                if existing_obj['class'] == new_cls:
                    # Calculate 2D Euclidean distance
                    dist = math.hypot(existing_obj['x'] - new_x, existing_obj['y'] - new_y)
                    if dist < self.distance_threshold and dist < min_dist:
                        min_dist = dist
                        matched_id = obj_id

            # Step 2: Update existing or Insert new
            if matched_id is not None:
                # [UPDATE EXISTING OBJECT]
                target_obj = self.spatial_memory[matched_id]
                
                # 1) Kalman Filter Processing
                kf = target_obj['kf']
                kf.predict()
                filtered_x, filtered_y, filtered_z = kf.update(new_x, new_y, new_z)

                target_obj['x'] = filtered_x
                target_obj['y'] = filtered_y
                target_obj['z'] = filtered_z
                target_obj['last_seen'] = current_time
                
                # 2) Increase belief score
                target_obj['belief'] = min(self.max_belief, target_obj['belief'] + self.belief_increment)
                
                # 3) Trigger callback only once when it crosses the confirm threshold
                if not target_obj['is_confirmed'] and target_obj['belief'] >= self.confirm_threshold:
                    target_obj['is_confirmed'] = True

                    print(f"[MapManager] ★ Object Confirmed! ID: {matched_id} ({new_cls})")
                    if self.on_new_object_callback:
                        safe_export_data = {
                            "id": matched_id,
                            "class": target_obj['class'],
                            "x": target_obj['x'],
                            "y": target_obj['y'],
                            "z": target_obj['z']
                        }
                        self.on_new_object_callback(safe_export_data)

            else:
                # [INSERT NEW CANDIDATE OBJECT]
                # Initialize a dedicated Kalman Filter for this specific object
                new_kf = KalmanFilter3D(new_x, new_y, new_z)

                new_obj_data = {
                    'class': new_cls,
                    'x': new_x,
                    'y': new_y,
                    'z': new_z,
                    'last_seen': current_time,
                    'belief': self.belief_increment, 
                    'is_confirmed': False,
                    'kf': new_kf  # Store the Kalman Filter instance inside the dictionary
                }
                
                self.spatial_memory[self.next_obj_id] = new_obj_data
                print(f"[MapManager] Candidate detected: ID {self.next_obj_id} ({new_cls}) - Belief: {self.belief_increment}")
                self.next_obj_id += 1

    def cleanup_stale_objects(self, current_time):
        """
        Evicts objects that haven't been seen for a while or lost their belief score.
        """
        to_delete = []

        for obj_id, obj in self.spatial_memory.items():
            elapsed_time = current_time - obj['last_seen']

            # Decay belief if not seen recently (e.g., > 0.5s)
            if elapsed_time > 0.5:
                obj['belief'] -= self.belief_decay_rate
            
            # Mark for deletion if belief drops to 0 or timeout is reached
            if obj['belief'] <= 0 or elapsed_time > self.stale_timeout:
                to_delete.append(obj_id)

        # Safely remove objects from memory
        for obj_id in to_delete:
            deleted_obj = self.spatial_memory.pop(obj_id)
            if deleted_obj['is_confirmed']:
                print(f"[MapManager] Object Evicted (Removed): ID {obj_id} ({deleted_obj['class']})")


    # ---------------------------------------------------------
    # Readers (Getters for other systems)
    # ---------------------------------------------------------
    def get_obstacles_for_costmap(self):
        """
        Reader 1: Nav2 Costmap
        Returns a clean list of (x, y) coordinates for the ROS 2 Nav2 stack.
        """
        current_time = time.time()
        active_obstacles = []
        for obj in self.spatial_memory.values():
            if obj['is_confirmed'] and (current_time - obj['last_seen'] < 60.0): 
                active_obstacles.append((obj['x'], obj['y']))
        return active_obstacles

    def export_session_data(self):
        """
        Reader 2: Cloud / DB / Digital Twin
        Returns the entire map as a GeoJSON-like dictionary when the session ends.
        """
        features = []
        for obj_id, obj in self.spatial_memory.items():
            if obj['is_confirmed']: # Only export confirmed objects
                features.append({
                    "id": obj_id,
                    "class": obj['class'],
                    "coordinates": [round(obj['x'], 2), round(obj['y'], 2)]
                })
            
        return {
            "session_end_time": time.time(),
            "total_objects_found": len(features),
            "features": features
        }
    

def map_manager_worker(manager: SemanticMapManager):
    print("[MapManager] Worker thread started.")
    while True:
        try:
            raw_detections = manager.source_queue.get()
            
            if raw_detections is None:
                break
                
            manager.update_with_raw_detections(raw_detections)
            
        except Exception as e:
            print(f"[MapManager] Error: {e}")