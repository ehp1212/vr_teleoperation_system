import asyncio
import numpy as np
from multiprocessing import Process, shared_memory, Event

from .webrtc.sync_coordinator import SyncCoordinator
from .ros.shm_subscriber import ros_worker_process, RgbVideoCallback, DepthVideoCallback
from .webrtc.shm_tracks import RgbVideoTrack, DepthVideoTrack
from .webrtc.webrtc_client import WebRTCClient
from .ros.tele_op_node import TeleopNode

STREAMS = {
    "rgb": {
        "topic": "/camera/rgb/image_raw",
        "shape": (480, 640, 3),
        "node_class": RgbVideoCallback,
        "format": "bgr24"
    },
    "depth": {
        "topic": "/camera/depth/image_raw",
        "shape": (240, 320),  
        "node_class": DepthVideoCallback,
        "format": "gray"
    },
}

async def async_main():
    shm_blocks = []
    processes = []
    coordinator = SyncCoordinator()
    tracks = {}

    try:
        # ===================================
        # Child Process
        # ===================================
        for name, config in STREAMS.items():
            shm_name = f"shm_{name}"
            byte_size = int(np.prod(config["shape"]) * 1)

            # create Shared Memory
            shm = shared_memory.SharedMemory(create=True, name=shm_name, size=byte_size)
            shm_blocks.append(shm)

            # Event
            mp_event = Event()
            coordinator.add_worker_event(name, mp_event)

            # Subprocess, ros2 worker
            args = (name, config["topic"], shm_name, config["shape"], mp_event)
            p = Process(target=ros_worker_process, args=(config["node_class"], args))
            p.start()
            processes.append(p)

            # WebRTC track
            if config["format"] == "bgr24":
                tracks[name] = RgbVideoTrack(name=name, shm_name=shm_name, shape=config["shape"], coordinator=coordinator)
            elif config["format"] == "gray":
                tracks[name] = DepthVideoTrack(name=name, shm_name=shm_name, shape=config["shape"], coordinator=coordinator)

        # ===================================
        # Main Process
        # ===================================
        import rclpy
        import threading
        from rclpy.executors import MultiThreadedExecutor

        rclpy.init()

        teleop_node = TeleopNode()
        executor = MultiThreadedExecutor()
        executor.add_node(teleop_node)
        
        ros_thread = threading.Thread(
            target=executor.spin,
            daemon=True
        )

        ros_thread.start()
        print("[System] TeleopNode")

        # ===================================
        # WebRTC loop
        # ===================================
        asyncio.create_task(coordinator.flush_loop())

        # WebRTC Client
        client = WebRTCClient(teleop_node, tracks)
        print("[System] Waiting for WebRTC...")
        await client.connect_loop()
    
    finally:
        print("[System] Cleaninig resources...")
        for p in processes:
            p.terminate()
            p.join()
        
        for shm in shm_blocks:
            shm.close()
            shm.unlink()

def main():
    asyncio.run(async_main())