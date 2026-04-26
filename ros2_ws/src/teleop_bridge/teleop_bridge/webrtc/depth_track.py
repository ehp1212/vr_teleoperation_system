import numpy as np
import cv2
from aiortc import VideoStreamTrack
from av import VideoFrame

import struct
import time

from teleop_bridge.utils.logger_extension_image import embed_metadata_gray_redundant
from teleop_bridge.utils.logger import logger


class DepthVideoTrack(VideoStreamTrack):
    def __init__(self, name):
        super().__init__()
        self.name = name

        self.latest_depth = None
        self.latest_ts = None
        self.latest_frame_id = None  

    def update(self, depth, timestamp, frame_id):
        self.latest_depth = depth
        self.latest_ts = timestamp
        self.latest_frame_id = frame_id

        logger.log(f"{self.name}_track_update", frame_id, timestamp)

    async def recv(self):
        pts, time_base = await self.next_timestamp()

        frame_id = self.latest_frame_id
        now = time.time()

        logger.log(f"{self.name}_recv_enter", frame_id, now)

        # depth → image 
        if self.latest_depth is None:
            img = np.zeros((240, 320), dtype=np.uint8)
            frame_id = -1
        else:
            depth = self.latest_depth

            max_depth = 5.0
            depth_norm = np.clip(depth / max_depth, 0, 1)

            img = (depth_norm * 255).astype(np.uint8)
            img = cv2.resize(img, (320, 240))

        # metadata 
        send_ts = time.time()

        img = embed_metadata_gray_redundant(
            img,
            frame_id=frame_id,
            timestamp=send_ts,
            repeat=8
        )

        logger.log(f"{self.name}_send", frame_id, send_ts)

        # VideoFrame 
        frame = VideoFrame.from_ndarray(img, format="gray")
        frame.pts = pts
        frame.time_base = time_base

        return frame