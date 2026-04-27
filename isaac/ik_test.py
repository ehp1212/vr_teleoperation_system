from isaacsim.core.prims import SingleArticulation
from isaacsim.robot_motion.motion_generation.lula import RmpFlow
from isaacsim.robot_motion.motion_generation import (
    interface_config_loader,
    ArticulationMotionPolicy,
)

import numpy as np
import omni.kit.app
import omni.timeline
import omni.ui as ui

# ----------------------------
# CONFIG
# ----------------------------
ROBOT_PATH = "/World/franka"  # must be the articulation root

# ----------------------------
# ROBOT
# ----------------------------
robot = SingleArticulation(ROBOT_PATH)

# ----------------------------
# MOTION POLICY
# ----------------------------
config = interface_config_loader.load_supported_motion_policy_config(
    "Franka",
    "RMPflow"
)
rmpflow = RmpFlow(**config)

policy = None
controller = None

# ----------------------------
# TARGET
# ----------------------------
target_position = np.array([0.5, 0.0, 0.5], dtype=np.float64)
target_orientation = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float64)

# ----------------------------
# STATE
# ----------------------------
initialized = False
frame_count = 0

app = omni.kit.app.get_app()
timeline = omni.timeline.get_timeline_interface()

# ----------------------------
# UI
# ----------------------------
window = ui.Window("EE Control", width=320, height=220)

with window.frame:
    with ui.VStack(spacing=8):
        ui.Label("End Effector Control")

        def update_x(v):
            global target_position
            target_position = np.array(
                [float(v), target_position[1], target_position[2]],
                dtype=np.float64,
            )
            print("Target:", target_position)

        def update_y(v):
            global target_position
            target_position = np.array(
                [target_position[0], float(v), target_position[2]],
                dtype=np.float64,
            )
            print("Target:", target_position)

        def update_z(v):
            global target_position
            target_position = np.array(
                [target_position[0], target_position[1], float(v)],
                dtype=np.float64,
            )
            print("Target:", target_position)

        ui.Label("X")
        ui.FloatSlider(min=0.2, max=0.8, value=0.5, on_value_changed_fn=update_x)

        ui.Label("Y")
        ui.FloatSlider(min=-0.5, max=0.5, value=0.0, on_value_changed_fn=update_y)

        ui.Label("Z")
        ui.FloatSlider(min=0.2, max=0.8, value=0.5, on_value_changed_fn=update_z)

# ----------------------------
# UPDATE LOOP
# ----------------------------
def update_fn(e):
    global initialized, frame_count, policy, controller

    if not timeline.is_playing():
        initialized = False
        frame_count = 0
        policy = None
        controller = None
        return

    frame_count += 1

    # Wait a few frames for PhysX to be ready
    if not initialized:
        if frame_count < 20:
            return

        try:
            robot.initialize()
            print("Robot initialized")
            print("DOF:", robot.num_dof)

            controller = robot.get_articulation_controller()
            policy = ArticulationMotionPolicy(robot, rmpflow)

            initialized = True
            print("Controller created")
            print("Policy created")
        except Exception as ex:
            print("Initialization error:", ex)

        return

    if policy is None or controller is None:
        return

    # Set IK target
    rmpflow.set_end_effector_target(
        target_position.copy(),
        target_orientation.copy()
    )

    # Update internal motion policy state
    rmpflow.update_world()

    # Compute action
    action = policy.get_next_articulation_action()

    print("Action:", action)

    if action is not None:
        controller.apply_action(action)

# ----------------------------
# SUBSCRIBE
# ----------------------------
sub = app.get_update_event_stream().create_subscription_to_pop(update_fn)

print("EE controller loaded")
