import struct
import time
import numpy as np

def embed_metadata_rgb_redundant(img, frame_id, timestamp, repeat=8):
    """
    img: uint8 BGR image (H, W, 3)
    """

    header = struct.pack("<Id", frame_id, timestamp)  # 12 bytes

    flat = img.reshape(-1)  # (H*W*3)

    idx = 0
    for b in header:
        for _ in range(repeat):
            if idx >= len(flat):
                break
            flat[idx] = b
            idx += 1

    return img

def embed_metadata_gray_redundant(img, frame_id, timestamp, repeat=8):
    """
    img: uint8 grayscale (H, W)
    frame_id: int
    timestamp: float
    repeat: redundancy factor
    """

    header = struct.pack("<Id", frame_id, timestamp)  # 12 bytes

    flat = img.reshape(-1)

    idx = 0
    for b in header:
        for _ in range(repeat):
            if idx >= len(flat):
                break
            flat[idx] = b
            idx += 1

    return img
