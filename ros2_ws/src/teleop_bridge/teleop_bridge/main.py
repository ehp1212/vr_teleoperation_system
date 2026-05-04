import asyncio
import numpy as np
from multiprocessing import Process, Queue, shared_memory, Event

from .webrtc.sync_coordinator import SyncCoordinator
from .ros.shm_subscriber import ros_worker_process, RgbVideoCallback, DepthVideoCallback
from .perception.perception_engine import perception_fusion_worker
from .webrtc.shm_tracks import RgbVideoTrack, DepthVideoTrack
from .webrtc.webrtc_client import WebRTCClient
from .robot_state_orchestrator import RobotStateOrchestrator

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

    # pipeline events
    img_recv_done_events = {}

    try:
        # ===================================
        # Camera images to shared memory
        # ===================================
        for name, config in STREAMS.items():
            try:
                # ------------------------------
                # Shared memory for images input and prcessing
                # ------------------------------
                shm_name = f"shm_{name}"
                byte_size = int(np.prod(config["shape"]))

                # create Shared Memory
                shm_raw = shared_memory.SharedMemory(create=True, name=shm_name, size=byte_size)
                shm_blocks.append(shm_raw)
            
                # callback to perception event
                img_recv_done_events[name] = Event()

                # Subprocess, ros2 worker
                args = (name, config["topic"], shm_name, config["shape"], img_recv_done_events[name])
                p = Process(target=ros_worker_process, args=(config["node_class"], args))
                p.start()
                processes.append(p)

                # ------------------------------
                # Shared memory for final images
                # ------------------------------
                shm_webrtc_name = f"{shm_name}_webrtc"
                shm_webrtc = shared_memory.SharedMemory(create=True, name=shm_webrtc_name, size=byte_size)
                shm_blocks.append(shm_webrtc)

            except Exception as e:
                print(f"[SYSTEM] Failed to initialize callbacks, {e}")


        # ===================================
        # Perception sensor fusion
        # ===================================
        # TODO: modulise per stream
        metadata_queue = Queue(maxsize=5)
        perception_done_event = Event()

        # check only perception fusion is done
        coordinator.add_worker_event("fusion_done", perception_done_event)    

        p_perc = Process(
            target=perception_fusion_worker,
            args=(
                "shm_rgb", "shm_depth",                                      # Data source
                STREAMS["rgb"]["shape"], STREAMS["depth"]["shape"],
                img_recv_done_events["rgb"], img_recv_done_events["depth"],  # Input waiting signal
                perception_done_event, metadata_queue,                       # Output waiting signal and Output
                "shm_rgb_webrtc", "shm_depth_webrtc"                         # Output shared memory name
            )
        )

        p_perc.start()
        processes.append(p_perc)

        # ===================================
        # WebRTC Transmission
        # ===================================
        for name, config in STREAMS.items():
            shm_name = f"shm_{name}_webrtc"
            if config["format"] == "bgr24":
                tracks[name] = RgbVideoTrack(name=name, shm_name=shm_name, shape=config["shape"], coordinator=coordinator)
            elif config["format"] == "gray":
                tracks[name] = DepthVideoTrack(name=name, shm_name=shm_name, shape=config["shape"], coordinator=coordinator)

        # ===================================
        # ROS2 Process  
        # ===================================
        shared_map_manager = None
        orchestrator = RobotStateOrchestrator(shared_map_manager)
     
        # ===================================
        # WebRTC loop
        # ===================================
        asyncio.create_task(coordinator.flush_loop())

        # WebRTC Client
        client = WebRTCClient(orchestrator.teleop_node, tracks)
        print("[System] Waiting for WebRTC...")
        await client.connect_loop()
    
    finally:
        print("[System] Cleaninig resources...")
        for p in processes:
            p.terminate()
            p.join()
        
        for shm_raw in shm_blocks:
            shm_raw.close()
            shm_raw.unlink()

def main():
    asyncio.run(async_main())