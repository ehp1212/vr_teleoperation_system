from multiprocessing import shared_memory
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


    def _process_fusion(self, rgb_img, depth_img):

        # --------------------
        # Perception 
        # --------------------
        # Perception
        # 1. rgb_img를 YOLO 모델에 넣고 BBox 좌표 추출
        # 2. BBox 중앙값(Center X, Y) 계산
        # 3. depth_img에서 (Center X, Y) 위치의 거리값 추출
        # 4. 추출된 데이터를 딕셔너리(JSON) 형태로 조립하여 리턴

        # --------------------
        # RGB ROI encoding 
        # --------------------
        h, w = rgb_img.shape[:2]

        # blur
        # blurred_img = cv2.GaussianBlur(rgb_img, (31, 31), 0)
        blurred_img = cv2.boxFilter(rgb_img, -1, (31, 31))

        # ROI region
        roi_ratio = 0.8
        roi_w, roi_h = int(w * roi_ratio), int(h * roi_ratio)
        x1 = (w - roi_w) // 2
        y1 = (h - roi_h) // 2
        x2 = x1 + roi_w
        y2 = y1 + roi_h

        # combined filtered and roi 
        # TODO: maybe Downsampling & Resizing  
        blurred_img[y1:y2, x1:x2] = rgb_img[y1:y2, x1:x2]
        rgb_img = blurred_img

        self._rgb_output_img[:] = rgb_img
        self._depth_output_img[:] = depth_img

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