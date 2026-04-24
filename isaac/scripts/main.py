import os
import sys
from isaacsim import SimulationApp

# 1. 앱 설정 (최적화)
CONFIG = {
    "width": 1280,
    "height": 720,
    "headless": False,
    "experience": "/home/eun/personal_project/humanoid_digital_twin/isaac/sim.kit"
}

sim_app = SimulationApp(CONFIG)

import omni.timeline
from omni.isaac.core.utils.extensions import enable_extension
from omni.isaac.core import World
from omni.isaac.core.utils.stage import open_stage

from camera_manager import CameraManager

def main():
    current_path = os.path.dirname(os.path.realpath(__file__))
    usd_path = os.path.abspath(os.path.join(current_path, "../usd/world/sim_layer.usd"))

    print(f"🎯 Loading USD from: {usd_path}")
    if not os.path.exists(usd_path):
        print(f"❌ Cannot find usd file: {usd_path}")
        sim_app.close()
        return
    
    open_stage(usd_path=usd_path)

    camera_manager = CameraManager("/World/ackermann_gimbal_robot/pitch_base/camera_link/Camera")

    world = World(stage_units_in_meters=1.0)
    world.reset() 

    timeline = omni.timeline.get_timeline_interface()
    timeline.play()
    
    frame_count = 0
    
    print("🚀 Simulation Started!")
    # camera_initialized = False
    while sim_app.is_running():
        world.step(render=True)

        # if not camera_initialized:
        #     camera_manager.on_simulation_start()
        #     camera_initialized = True

        frame_count += 1
        if frame_count % 1000 == 0:
            print(f"Simulation is running... (Frame: {frame_count})")

    # camera_manager.on_simulation_end()
    sim_app.close()

if __name__ == "__main__":
    main()