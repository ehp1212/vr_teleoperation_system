from multiprocessing import shared_memory
from ultralytics import YOLO

import numpy as np
import cv2
import time
from scipy.spatial.transform import Rotation as R

class PerceptionFusionEngine:
    def __init__(
            self,
            shm_rgb_name,
            shm_depth_name,
            rgb_shape,
            depth_shape,
            rgb_dtype,
            depth_dtype,
            rgb_event,
            depth_event,
            perception_done_event,
            pose_shared_dict,
            metadata_queue,
            shm_rgb_webrtc_name,
            shm_depth_webrtc_name,
        ):
        
        # Initialisation
        # TODO: Perception logging
        self._shm_rgb_name = shm_rgb_name
        self._shm_depth_name = shm_depth_name
        self._rgb_dtype = np.dtype(rgb_dtype)
        self._depth_dtype = np.dtype(depth_dtype)

        self._rgb_shape = rgb_shape
        self._depth_shape = depth_shape

        self._rgb_done_event = rgb_event
        self._depth_done_event = depth_event
        self._perception_done_event = perception_done_event
        
        self._pose_shared_dict = pose_shared_dict
        self._metadata_queue = metadata_queue

        # Conect to shared memory
        self._rgb_shm = shared_memory.SharedMemory(name=self._shm_rgb_name)
        self._rgb_img = np.ndarray(
            self._rgb_shape,
            dtype=self._rgb_dtype,
            buffer=self._rgb_shm.buf
        )

        self._depth_shm = shared_memory.SharedMemory(name=self._shm_depth_name)
        self._depth_img = np.ndarray(
            self._depth_shape,
            dtype=self._depth_dtype,
            buffer=self._depth_shm.buf
        )

        # Connect to output shared memory
        self._shm_rgb_output_name = shm_rgb_webrtc_name
        self._shm_depth_output_name = shm_depth_webrtc_name
        
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
        try:
            # --------------------
            # 0. Get Camera World Pose 
            # --------------------
            cam_pose = dict(self._pose_shared_dict)

            # --------------------
            # 1. Perception
            # --------------------
            results = self.model(rgb_img, verbose=False)

            h, w = rgb_img.shape[:2]
            depth_h, depth_w = depth_img.shape[:2]
            sx = depth_w / w
            sy = depth_h / h

            fx, fy, cx, cy = self._get_pixel_intrinsics(image_width=w, image_height=h)

            frame_metadata = []

            for box in results[0].boxes:
                # Extract original BBox coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0].cpu().numpy())
                conf = float(box.conf[0].cpu().numpy())
                cls_name = self.model.names[int(box.cls[0].cpu().numpy())]
                
                if conf < 0.5:
                    continue

                dx1 = int(x1 * sx)
                dy1 = int(y1 * sy)
                dx2 = int(x2 * sx)
                dy2 = int(y2 * sy)

                # --------------------
                # 1. Get Depth 
                # --------------------
                # z_target_meters = self._get_roi_depth(dx1, dy1, dx2, dy2, depth_img)

                # --------------------
                # 2. Calculate the center pixel (u, v) of the bounding box
                # --------------------
                u_center = (x1 + x2) / 2.0  # 검출된 박스의 가로 중앙
                v_center = (y1 + y2) / 2.0  # 검출된 박스의 세로 중앙

                target_u = int(u_center * sx)
                target_v = int(v_center * sy)

                # 안전 장치 (이미지 경계값 제한)
                target_u = max(0, min(target_u, depth_w - 1))
                target_v = max(0, min(target_v, depth_h - 1))

                z_target_meters = depth_img[target_v, target_u]

                # --------------------
                # 3. Project to 3D Space
                # --------------------
                X_opt, Y_opt, Z_opt = self._project_pixel_to_3d_optical(
                        u_center, v_center, z_target_meters, fx, fy, cx, cy
                    )

                # --------------------
                # 4. Optical Frame -> World(Map) Frame
                # --------------------
                local_point = np.array([Z_opt, -X_opt, -Y_opt])

                cam_rotation = R.from_quat([
                    cam_pose.get('qx', 0.0), cam_pose.get('qy', 0.0), 
                    cam_pose.get('qz', 0.0), cam_pose.get('qw', 1.0)
                ])
                cam_translation = np.array([
                    cam_pose.get('x', 0.0), cam_pose.get('y', 0.0), cam_pose.get('z', 0.0)
                ])

                # Calculate world position
                world_point = cam_rotation.apply(local_point) + cam_translation
                X_world, Y_world, Z_world = world_point[0], world_point[1], world_point[2]

                # --------------------
                # 5. Metadata
                # --------------------
                obj_data = {
                    "class": cls_name,
                    "confidence": round(conf, 2),
                    "x": round(float(X_world), 3),
                    "y": round(float(Y_world), 3),
                    "z": round(float(Z_world), 3),
                    "last_seen": time.time()
                }

                print(obj_data)

                frame_metadata.append(obj_data)

                # [Debug] Draw Green Box
                cv2.rectangle(rgb_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # [Debug] Print 3D coordinates on screen!
                text_3d = f"[{obj_data['x']:.1f}, {obj_data['y']:.1f}, {obj_data['z']:.1f}]"
                cv2.putText(rgb_img, text_3d, (x1, y1 - 10), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            if frame_metadata:
                try:
                    # 큐가 가득 차지 않았다면 전송 (블로킹 방지)
                    self._metadata_queue.put_nowait(frame_metadata)
                except Exception as e:
                    pass # Queue Full 시 가장 오래된/현재 프레임 버림 처리 (선택적 구현)
            
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
            self._depth_output_img[:] = self.depth_to_uint8_gray(depth_img)
        except Exception as e:
            print(e)

    # ==============================
    # DETECTION
    # ==============================
    def _get_roi_depth(self, x1, y1, x2, y2, depth_img):
        depth_h, depth_w = depth_img.shape[:2]

        x1 = max(0, min(int(x1), depth_w - 1))
        x2 = max(0, min(int(x2), depth_w))
        y1 = max(0, min(int(y1), depth_h - 1))
        y2 = max(0, min(int(y2), depth_h))

        if x2 <= x1 or y2 <= y1:
            return 0.0

        bbox_depth = depth_img[y1:y2, x1:x2]
        h, w = bbox_depth.shape[:2]

        if h == 0 or w == 0:
            return 0.0

        min_valid_depth = 0.3
        max_valid_depth = 5.5

        def valid_median(region):
            vals = region[np.isfinite(region)]
            vals = vals[(vals >= min_valid_depth) & (vals <= max_valid_depth)]
            if vals.size == 0:
                return 0.0
            return float(np.median(vals))

        # 1. 중앙 50%
        roi_ratio = 0.5
        roi_x1 = int(w * (1.0 - roi_ratio) / 2.0)
        roi_x2 = int(w * (1.0 + roi_ratio) / 2.0)
        roi_y1 = int(h * (1.0 - roi_ratio) / 2.0)
        roi_y2 = int(h * (1.0 + roi_ratio) / 2.0)

        inner_roi = bbox_depth[roi_y1:roi_y2, roi_x1:roi_x2]
        z = valid_median(inner_roi)
        if z > 0.0:
            return z

        # 2. 전체 bbox fallback
        z = valid_median(bbox_depth)
        if z > 0.0:
            return z

        # 3. 마지막 디버그용 fallback: 0.0보다 큰 값이라도 반환
        vals = bbox_depth[np.isfinite(bbox_depth)]
        vals = vals[vals > 0.0]
        if vals.size == 0:
            return 0.0

        return float(np.median(vals))

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

    def _project_pixel_to_3d_optical(self, u, v, z_depth, fx, fy, cx, cy):
        X_opt = (u - cx) * z_depth / fx
        Y_opt = (v - cy) * z_depth / fy
        Z_opt = z_depth
        return X_opt, Y_opt, Z_opt
    
    def depth_to_uint8_gray(self, depth, min_depth=0.2, max_depth=10.0):
        """
        depth: float32 depth image in meters, shape (H, W)
        return: uint8 grayscale image, shape (H, W)
        """
        depth = np.asarray(depth, dtype=np.float32)

        valid = np.isfinite(depth)
        clipped = np.clip(depth, min_depth, max_depth)

        normalized = (clipped - min_depth) / (max_depth - min_depth)
        gray = (normalized * 255.0).astype(np.uint8)

        gray[~valid] = 0
        return gray


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