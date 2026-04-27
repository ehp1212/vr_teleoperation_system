import time
import asyncio
import numpy as np
from aiortc import VideoStreamTrack
from av import VideoFrame

from teleop_bridge.utils.logger_extension_image import embed_metadata_rgb_redundant
from teleop_bridge.utils.logger import logger

class SimpleVideoTrack(VideoStreamTrack):
    def __init__(self, name):
        super().__init__()

        self.name = name
        self.latest_frame = None        
        self.latest_frame_id = None     
        self.latest_ts = None           

    def update(self, rgb, timestamp, frame_id):
        self.latest_frame = rgb
        self.latest_frame_id = frame_id
        self.latest_ts = timestamp

        logger.log(f"{self.name}_track_update", frame_id, timestamp)

    async def recv(self):

        try:
            pts, time_base = await self.next_timestamp()
            
            # frame_id
            frame_id = self.latest_frame_id

            now = time.time()
            logger.log("recv_enter", frame_id, now, extra={"stream": "rgb"})

            # frame 
            if self.latest_frame is None:
                img = np.zeros((480, 640, 3), dtype=np.uint8)
                frame_id = -1  # fallback
            else:
                img = self.latest_frame.copy()

            # metadata 
            send_ts = time.time()

            img = embed_metadata_rgb_redundant(
                img,
                frame_id=frame_id,
                timestamp=send_ts,
                repeat=8
            )

            logger.log("recv_send", frame_id, send_ts, extra={"stream": "rgb"})
            
            # VideoFrame
            video_frame = VideoFrame.from_ndarray(img, format="bgr24")
            video_frame.pts = pts
            video_frame.time_base = time_base

            return video_frame
        
        except Exception as e:
            print(f"RECV ERROR: ", e)
            pass