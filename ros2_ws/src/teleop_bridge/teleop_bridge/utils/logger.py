import json
import time
import os

class Logger:
    """
    [Bridge Integrated Pipeline Profiling]
    -----------------------------------------------------------------------------
    < Python Domain >
    T0_a (capture_done) : Image arrival from ROS2 node.
    T0_b (send_request) : WebRTC track retrieval (embedded in barcode).

    < Unity Domain (Received via DataChannel/API) >
    T1 (recv_request)    : Unity detected the frame and requested GPU readback.
    T2 (recv_arrival)    : GPU-to-CPU transfer complete.
    T3 (recv_decode_done): Barcode scan complete (Frame ID verified).
    T4 (recv_sync_done)  : Multi-stream synchronization finalized in Unity.

    < Analysis Formulae >
    - Internal Bridge Delay : T0_b - T0_a
    - Network + Encode Delay: T1 - T0_b (Includes Clock Offset)
    - Unity GPU Overhead   : T2 - T1
    - Final E2E Latency    : T4 - T0_a (Corrected by Offset)
    -----------------------------------------------------------------------------
    """
    
    def __init__(self, filename="log.jsonl"):
        self.session_id = int(time.time())
        self.file = open(filename, "w")

    def log(self, stage, frame_id, timestamp=None, extra=None):
        if timestamp is None:
            timestamp = time.time()

        entry = {
            "session": self.session_id,
            "stage": stage,
            "frame_id": frame_id,
            "ts": timestamp
        }

        if extra:
            entry.update(extra)
        
        self.file.write(json.dumps(entry) + "\n")
        self.file.flush()

logger = Logger("ros_log.jsonl")