import time
import numpy as np

from aiortc import VideoStreamTrack
from av import VideoFrame
from multiprocessing import shared_memory

class ShmVideoTrack(VideoStreamTrack):
    def __init__(self, name, shm_name, shape, coordinator, format="bgr24"):
        super().__init__()
        self.name = name
        self.shape = shape
        self.coordinator = coordinator
        self.format = format

        # shared memory
        self.shm = shared_memory.SharedMemory(name=shm_name)
        self.shared_view = np.ndarray(self.shape, dtype=np.uint8, buffer=self.shm.buf)

    def embed_barcode(self, frame_id, current_time_ms):
        raise NotImplementedError("embeded process not implemented")

    async def recv(self):
        """
        In order to pass frame_id, convert value to barcoded images
        Maximum value for frame_id: 32 bits
        """
        
        # Waiting for coordinator
        await self.coordinator.webrtc_ready_event.wait()

        pts, time_base = await self.next_timestamp()

        # ------------------------------
        # Embed frame_id
        # ------------------------------
        frame_id = self.coordinator.global_frame_id
        t0_b = int(time.time() * 1000) & 0xFFFFFFFF
        self.logger.log("send_request", self.current_frame_id, t0_b, self.name)

        self.embed_barcode(frame_id, t0_b)

        frame = VideoFrame.from_ndarray(self.shared_view, format=self.format)
        frame.pts = pts
        frame.time_base = time_base
        
        return frame
    
class RgbVideoTrack(ShmVideoTrack):
    def __init__(self, name, shm_name, shape, coordinator):
        super().__init__(name, shm_name, shape, coordinator, "bgr24")

    def embed_barcode(self, frame_id, current_time_ms):
        
        # Barcode Embedding 32 bit
        for i in range(32):
            bit_is_one = (frame_id >> i) & 1
            color = 255 if bit_is_one else 0

            bit_ts = (current_time_ms >> i) & 1
            color_ts = 255 if bit_ts else 0

            start_x = i * 4
            self.shared_view[0:4, start_x : start_x + 4] = [color, color, color]
            self.shared_view[4:8, start_x : start_x + 4] = [color_ts, color_ts, color_ts]

class DepthVideoTrack(ShmVideoTrack):
    def __init__(self, name, shm_name, shape, coordinator):
        super().__init__(name, shm_name, shape, coordinator, "gray")

    def embed_barcode(self, frame_id, current_time_ms):
        
        for i in range(32):
            bit_id = (frame_id >> i) & 1
            color_id = 255 if bit_id else 0
            
            bit_ts = (current_time_ms >> i) & 1
            color_ts = 255 if bit_ts else 0
            
            start_x = i * 4
            
            self.shared_view[0:4, start_x : start_x + 4] = color_id
            self.shared_view[4:8, start_x : start_x + 4] = color_ts