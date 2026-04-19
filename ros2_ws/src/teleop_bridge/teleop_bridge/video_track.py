import asyncio
import numpy as np
from aiortc import VideoStreamTrack
from av import VideoFrame

class SimpleVideoTrack(VideoStreamTrack):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.latest_frame = None

    async def recv(self):

        await asyncio.sleep(1/30)
        pts, time_base = await self.next_timestamp()

        if self.latest_frame is None:
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
        else:
            frame = self.latest_frame

        video_frame = VideoFrame.from_ndarray(frame, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base

        return video_frame