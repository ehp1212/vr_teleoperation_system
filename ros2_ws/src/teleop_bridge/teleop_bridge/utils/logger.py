import json
import time
import os

class Logger:
    def __init__(self, filename="log.jsonl"):
        self.file = open(filename, "w")

    def log(self, stage, frame_id, timestamp=None, extra=None):
        if timestamp is None:
            timestamp = time.time()

        entry = {
            "stage": stage,
            "frame_id": frame_id,
            "ts": timestamp
        }

        if extra:
            entry.update(extra)

        self.file.write(json.dumps(entry) + "\n")
        self.file.flush()

logger = Logger("ros_log.jsonl")