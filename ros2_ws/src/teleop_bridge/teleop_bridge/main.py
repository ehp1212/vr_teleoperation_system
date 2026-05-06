import asyncio
import threading

import numpy as np
from multiprocessing import Manager, Process, Queue, shared_memory, Event

from .webrtc.sync_coordinator import SyncCoordinator
from .ros.shm_subscriber import ros_worker_process, RgbVideoCallback, DepthVideoCallback
from .perception.perception_engine import perception_fusion_worker
from .webrtc.shm_tracks import RgbVideoTrack, DepthVideoTrack
from .webrtc.webrtc_client import WebRTCClient
from .robot_state_orchestrator import RobotStateOrchestrator
from .semantic_map_manager import SemanticMapManager, map_manager_worker

STREAMS = {
    "rgb": {
        "topic": "/camera/rgb/image_raw",
        "shape": (480, 640, 3),
        "dtype": np.uint8,
        "node_class": RgbVideoCallback,
        "format": "bgr24"
    },
    "depth": {
        "topic": "/camera/depth/image_raw",
        "shape": (240, 320),  
        "dtype": np.float32,
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
                # byte_size = int(np.prod(config["shape"]))
                dtype = np.dtype(config["dtype"])
                shape = config["shape"]
                byte_size = int(np.prod(shape) * dtype.itemsize)

                # create Shared Memory
                shm_raw = shared_memory.SharedMemory(create=True, name=shm_name, size=byte_size)
                shm_blocks.append(shm_raw)
            
                # callback to perception event
                img_recv_done_events[name] = Event()

                # Subprocess, ros2 worker
                args = (
                    name,
                    config["topic"],
                    shm_name,
                    config["shape"],
                    config["dtype"],
                    img_recv_done_events[name],
                )

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



        # TODO: Perception and ROS2 State should have robot tf source
        # ===================================
        # Global components
        # ===================================
        manager = Manager()

        # Perception -> map manger
        metadata_queue = Queue(maxsize=5)
        sementic_map_manager = SemanticMapManager(metadata_queue, 0.2)

        map_thread = threading.Thread(target=map_manager_worker, args=(sementic_map_manager,), daemon=True)
        map_thread.start()

        # ROS2 Callback -> Perception
        pose_shared_dict = manager.dict({
            'stamp_sec': 0,
            'stamp_nanosec': 0,
            'frame_id': 'map',
            'child_frame_id': 'camera_link',
            'x': 0.0, 'y': 0.0, 'z': 0.0,
            'qx': 0.0, 'qy': 0.0, 'qz': 0.0, 'qw': 1.0
        })

        # ===================================
        # Perception sensor fusion
        # ===================================
        # TODO: modulise per stream
        perception_done_event = Event()

        # check only perception fusion is done
        coordinator.add_worker_event("fusion_done", perception_done_event)    

        p_perc = Process(
            target=perception_fusion_worker,
            args=(
                "shm_rgb",
                "shm_depth",

                STREAMS["rgb"]["shape"],
                STREAMS["depth"]["shape"],

                STREAMS["rgb"]["dtype"],
                STREAMS["depth"]["dtype"],

                img_recv_done_events["rgb"],
                img_recv_done_events["depth"],

                perception_done_event,
                pose_shared_dict,
                metadata_queue,

                "shm_rgb_webrtc",
                "shm_depth_webrtc",
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
        orchestrator = RobotStateOrchestrator(sementic_map_manager, pose_shared_dict)
     
        # ===================================
        # WebRTC loop
        # ===================================
        asyncio.create_task(coordinator.flush_loop())

        # WebRTC Client
        client = WebRTCClient(orchestrator.teleop_node, tracks)
        print("[System] Waiting for WebRTC...")

        sementic_map_manager.set_new_object_callback(callback=client.on_add_new_object)
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