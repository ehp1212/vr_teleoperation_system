import time
from isaac.scripts.camera import IsaacCamera

def run():
    cam = IsaacCamera()

    print("Camera initialized")

    while True:
        frame = cam.get_frame()

        if frame is not None:
            print("Frame:", frame.shape)
        else:
            print("No frame")

        time.sleep(0.03)  # ~30fps