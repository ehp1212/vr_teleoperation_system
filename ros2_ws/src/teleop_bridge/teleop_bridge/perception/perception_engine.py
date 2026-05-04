from multiprocessing import shared_memory
from ultralytics import YOLO

import numpy as np
import cv2
import time

class PerceptionFusionEngine:
    def __init__(
            self, shm_rgb_name, shm_depth_name, 
            rgb_shape, depth_shape,
            rgb_recv_done_event, depth_recv_done_event,
            perception_done_event, metadata_queue,
            shm_rgb_output_name, shm_depth_output_name
        ):
        
        # Initialisation
        # TODO: Perception logging
        self._shm_rgb_name = shm_rgb_name
        self._shm_depth_name = shm_depth_name
        self._rgb_shape = rgb_shape
        self._depth_shape = depth_shape

        self._rgb_done_event = rgb_recv_done_event
        self._depth_done_event = depth_recv_done_event
        self._perception_done_event = perception_done_event
        
        self._metadata_queue = metadata_queue

        # Conect to shared memory
        self._rgb_shm = shared_memory.SharedMemory(name=self._shm_rgb_name)
        self._rgb_img = np.ndarray(self._rgb_shape, dtype=np.uint8, buffer=self._rgb_shm.buf)

        self._depth_shm = shared_memory.SharedMemory(name=self._shm_depth_name)
        self._depth_img = np.ndarray(self._depth_shape, dtype=np.uint8, buffer=self._depth_shm.buf)

        # Connect to output shared memory
        self._shm_rgb_output_name = shm_rgb_output_name
        self._shm_depth_output_name = shm_depth_output_name

        self._rgb_output_shm = shared_memory.SharedMemory(name=self._shm_rgb_output_name)
        self._rgb_output_img = np.ndarray(self._rgb_shape, dtype=np.uint8, buffer=self._rgb_output_shm.buf)

        self._depth_output_shm = shared_memory.SharedMemory(name=self._shm_depth_output_name)
        self._depth_output_img = np.ndarray(self._depth_shape, dtype=np.uint8, buffer=self._depth_output_shm.buf)

        # TODO: YOLO
        print(f"[Perception] Loading YOLOv8n model...")
        self.model = YOLO('yolov8n.pt')
        print(f"[Perception] Model loaded successfully")

    # ==============================
    # PUBLIC
    # ==============================
    def run(self):
        while True:
            try:
                self._rgb_done_event.wait()
                self._depth_done_event.wait()

                self._rgb_done_event.clear()
                self._depth_done_event.clear()

                self._process_fusion(self._rgb_img, self._depth_img)

                # pass to WebRTC track
                self._perception_done_event.set()

                time.sleep(0.005)

            except Exception as e:
                print(f"[Perception] Error: {e}")

    def cleanup(self):
        try:
            self._rgb_shm.close()
            self._depth_shm.close()
            self._rgb_output_shm.close()
            self._depth_output_shm.close()
            print("[Perception] Shared Memory closed safely.")
        except Exception as e:
            print(f"[Perception] Cleanup Error: {e}")
    
    # ==============================
    # INTERNAL
    # ==============================
    def _process_fusion(self, rgb_img, depth_img):

        # --------------------
        # 1. Perception
        # --------------------
        results = self.model(rgb_img, verbose=False)

        h, w = rgb_img.shape[:2]
        fx, fy, cx, cy = self._get_pixel_intrinsics(image_width=w, image_height=h)

        frame_metadata = []

        for box in results[0].boxes:
            # Extract original BBox coordinates
            x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
            conf = float(box.conf[0].cpu().numpy())
            cls_name = self.model.names[int(box.cls[0].cpu().numpy())]

            if conf < 0.5:
                continue

            # 1. Get Depth (Option B)
            z_target = self._get_roi_depth(x1, y1, x2, y2, depth_img)

            if z_target == 0:
                continue
                
            # 2. Calculate the center pixel (u, v) of the bounding box
            u_center = (x1 + x2) / 2.0
            v_center = (y1 + y2) / 2.0

            # 3. Project to 3D Space!
            X_3d, Y_3d, Z_3d = self._project_pixel_to_3d(
                u_center, v_center, z_target, fx, fy, cx, cy
            )

            # 4. Assemble the metadata dictionary
            obj_data = {
                "class": cls_name,
                "confidence": round(conf, 2),
                "position_3d_xyz": [round(X_3d, 2), round(Y_3d, 2), round(Z_3d, 2)]
            }

            frame_metadata.append(obj_data)

            # [Debug] Draw Green Box
            cv2.rectangle(rgb_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # [Debug] Print 3D coordinates on screen!
            text_3d = f"[{X_3d:.1f}, {Y_3d:.1f}, {Z_3d:.1f}]"
            cv2.putText(rgb_img, text_3d, (x1, y1 - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            print(f"[METADATA] Created: {obj_data}")
 
        # --------------------
        # 2. RGB ROI Encoding (Blurring background)
        # --------------------   
        h, w = rgb_img.shape[:2]

        # Apply box filter for blurring
        blurred_img = cv2.boxFilter(rgb_img, -1, (31, 31))

        # Define clear ROI region (center 80%)
        roi_ratio = 0.8
        roi_w, roi_h = int(w * roi_ratio), int(h * roi_ratio)
        roi_x1 = (w - roi_w) // 2
        roi_y1 = (h - roi_h) // 2
        roi_x2 = roi_x1 + roi_w
        roi_y2 = roi_y1 + roi_h

        # Restore original sharp image inside the center ROI
        blurred_img[roi_y1:roi_y2, roi_x1:roi_x2] = rgb_img[roi_y1:roi_y2, roi_x1:roi_x2]

        # Overwrite output shared memory
        self._rgb_output_img[:] = blurred_img
        self._depth_output_img[:] = depth_img

    # ==============================
    # DETECTION
    # ==============================
    def _get_roi_depth(self, x1, y1, x2, y2, depth_img):
        """
        Extract median depth from the central 50% ROI of the bounding box.
        """
        # Crop depth image to BBox size
        bbox_depth = depth_img[y1:y2, x1:x2]
        h, w = bbox_depth.shape

        # Prevent out-of-bounds error
        if h == 0 or w == 0:
            return 0

        # Define inner 50% ROI
        roi_ratio = 0.5
        roi_x1 = int(w * (1 - roi_ratio) / 2)
        roi_x2 = int(w * (1 + roi_ratio) / 2)
        roi_y1 = int(h * (1 - roi_ratio) / 2)
        roi_y2 = int(h * (1 + roi_ratio) / 2)

        inner_roi = bbox_depth[roi_y1:roi_y2, roi_x1:roi_x2]

        # Filter valid depth pixels (> 0)
        valid_depths = inner_roi[inner_roi > 0]

        if len(valid_depths) == 0:
            return 0

        # Calculate median depth
        z_target = float(np.median(valid_depths))

        # [TEMPORARILY DISABLED] Max Range Exception
        # We need to check what unit z_target is in the console first!
        # if z_target > 4.5:
        #     return 0

        return z_target

    def _refine_bbox_with_depth(self, x1, y1, x2, y2, depth_img):
        """
        Refine Bbox with depth textures
        """
        # get depths
        bbox_depth = depth_img[y1:y2, x1:x2]

        h, w = bbox_depth.shape
        roi_region = 0.5 
        roi_x1, roi_x2 = int(w * (roi_region / 2)), int(w * (roi_region / 2 + roi_region)) 
        roi_y1, roi_y2 = int(h * (roi_region / 2)), int(h * (roi_region / 2 + roi_region)) 
        inner_roi = bbox_depth[roi_y1:roi_y2, roi_x1:roi_x2]

        # get distance from roi
        valid_depths = inner_roi[inner_roi > 0]

        # return original if no depth data
        if len(valid_depths) == 0:
            return x1, y1, x2, y2, 0
        
        z_target = np.median(valid_depths)
        # if z_target > 5:
        #     return x1, y1, x2, y2, 0
        
        # masking
        margin = 50
        mask = cv2.inRange(bbox_depth, z_target - margin, z_target + margin)

        kernel = np.ones((5,5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel) 
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        # get new bbox
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return x1, y1, x2, y2, z_target
            
        largest_contour = max(contours, key=cv2.contourArea)
        rx, ry, rw, rh = cv2.boundingRect(largest_contour)
        
        new_x1 = x1 + rx
        new_y1 = y1 + ry
        new_x2 = new_x1 + rw
        new_y2 = new_y1 + rh
        
        return new_x1, new_y1, new_x2, new_y2, z_target

    # ==============================
    # PROJECTION TO 3D
    # ==============================
    def _get_pixel_intrinsics(self, image_width, image_height):
            """
            Convert physical Isaac Sim camera parameters (mm) to pixel-based intrinsic matrix values.
            """
            # Data from Isaac Sim properties panel
            focal_length_mm = 18.14756
            horiz_aperture_mm = 20.955
            vert_aperture_mm = 15.2908

            # Calculate pixel-based focal lengths
            fx = (focal_length_mm / horiz_aperture_mm) * float(image_width)
            fy = (focal_length_mm / vert_aperture_mm) * float(image_height)

            # Optical center is exactly the middle of the image
            cx = image_width / 2.0
            cy = image_height / 2.0

            return fx, fy, cx, cy

    def _project_pixel_to_3d(self, u, v, z_depth, fx, fy, cx, cy):
        """
        Project a 2D pixel coordinate (u, v) and depth (Z) into a 3D coordinate (X, Y, Z)
        using the Pinhole Camera Model.
        """
        # Pinhole projection formula
        X = (u - cx) * z_depth / fx
        Y = (v - cy) * z_depth / fy
        Z = z_depth

        return X, Y, Z


def perception_fusion_worker(*args):

    engine = PerceptionFusionEngine(*args)

    try:
        engine.run()
    except Exception as e:
        if e is KeyboardInterrupt:
            pass
        else:
            print("[Perception] Error, " + e)
    finally:
        engine.cleanup()