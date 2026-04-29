import time
import numpy as np
import cv2
from multiprocessing import shared_memory

class FakeImageWorker:
    def __init__(self, name, shm_name, shape, mp_event, target_fps=30):
        self.name = name
        self.shape = shape
        self.mp_event = mp_event
        self.target_fps = target_fps
        
        # 공유 메모리 연결
        self.shm = shared_memory.SharedMemory(name=shm_name)
        self.shared_array = np.ndarray(self.shape, dtype=np.uint8, buffer=self.shm.buf)
        print(f"[{self.name}] 가짜 데이터 생성기 가동 시작!")

    def run(self):
        frame_id = 0
        base_img = np.zeros(self.shape, dtype=np.uint8)
        
        try:
            while True:
                start_time = time.time()

                # 1. 인코더를 괴롭히기 위한 동적 이미지 생성 (그라데이션 및 텍스트 변화)
                # 매 프레임 배경색이 미세하게 바뀌도록 설정
                r = (frame_id * 3) % 255
                b = 255 - ((frame_id * 2) % 255)
                base_img[:] = (b, 128, r) # BGR 포맷
                
                # 화면 한가운데에 크게 프레임 정보 찍기
                cv2.putText(base_img, f"{self.name} | FPS: {self.target_fps}", 
                            (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
                cv2.putText(base_img, f"FRAME: {frame_id}", 
                            (50, 280), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 255), 4)

                # 2. 공유 메모리에 덮어쓰기 (In-place)
                self.shared_array[:] = base_img
                
                # 3. 메인 프로세스에 신호 보내기
                self.mp_event.set()
                frame_id += 1

                # 4. 목표 FPS 맞추기 (예: 30fps = 0.033초 대기)
                elapsed = time.time() - start_time
                sleep_time = max(0, (1.0 / self.target_fps) - elapsed)
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            pass
        finally:
            self.shm.close()

# 멀티프로세싱 Entry Point
def run_fake_worker(args):
    name, shm_name, shape, mp_event = args
    worker = FakeImageWorker(name, shm_name, shape, mp_event, target_fps=30)
    worker.run()