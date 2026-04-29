import asyncio
import time

class SyncCoordinator:
    def __init__(self):
        
        # Done event for workers
        self.worker_events = {}

        self.webrtc_ready_event = asyncio.Event()

        self.global_frame_id = 0

    def add_worker_event(self, stream_name, mp_event):
        self.worker_events[stream_name] = mp_event

    async def flush_loop(self):
        """
        Waiting for workers and flush together
        """
        while True:
            while not all(e.is_set() for e in self.worker_events.values()):                
                await asyncio.sleep(0.002) # 2ms wait

            self.global_frame_id += 1

            # Read 
            self.webrtc_ready_event.set()

            await asyncio.sleep(0.01)

            self.webrtc_ready_event.clear()
            for e in self.worker_events.values():
                e.clear()
            