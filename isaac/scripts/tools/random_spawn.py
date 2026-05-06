import random
import numpy as np
import omni.usd
from omni.isaac.core.utils.prims import get_prim_at_path, delete_prim, is_prim_path_valid
from omni.isaac.core.prims import XFormPrim
from omni.isaac.core.utils.rotations import euler_angles_to_quat
import omni.kit.commands

# --- Basic Stage Setup ---
STAGE = omni.usd.get_context().get_stage()
CANDIDATES_PATH = "/World/Candidates"
INSTANCES_GROUP_PATH = "/World/Instances"

def populate_slots_with_random_items():
    # --- [Step 1] Access Candidate Prims ---
    candidates_prim = STAGE.GetPrimAtPath(CANDIDATES_PATH)
    if not candidates_prim or not candidates_prim.IsValid():
        print(f"❌ Cannot find candidates path: {CANDIDATES_PATH}")
        return

    candidates = candidates_prim.GetChildren()
    if not candidates:
        print("❌ No candidates found.")
        return

    # --- [Step 2] Access Position Slots ---
    instances_group_prim = STAGE.GetPrimAtPath(INSTANCES_GROUP_PATH)
    if not instances_group_prim or not instances_group_prim.IsValid():
        print(f"❌ Cannot find instances group path: {INSTANCES_GROUP_PATH}")
        return

    slots = instances_group_prim.GetChildren()
    if not slots:
        print("❌ No position slots found under instances.")
        return

    # --- [Step 3] Spawn items into each slot ---
    instance_counter = 0

    for slot in slots:
        slot_path = str(slot.GetPath())
        
        # 3-1. Cleanup Phase: Delete previously spawned items inside this specific slot
        for child in slot.GetChildren():
            delete_prim(str(child.GetPath()))
            
        # 3-2. Pick a random candidate from the list
        random_candidate = random.choice(candidates)
        candidate_path = str(random_candidate.GetPath())
        candidate_name = random_candidate.GetName()
        
        # Define the new path (make the spawned item a child of the slot)
        new_item_path = f"{slot_path}/{candidate_name}"
        
        # 3-3. Copy the candidate into the slot
        omni.kit.commands.execute('CopyPrims',
            paths_from=[candidate_path],
            paths_to=[new_item_path]
        )
        
        # 3-4. Reset local transform (Relative to the parent slot)
        item_prim = XFormPrim(prim_path=new_item_path)
        
        # Set local position to (0, 0, 0) so it matches the slot's position perfectly.
        # Set local orientation to identity [w, x, y, z] so it inherits the slot's rotation.
        # (Uncomment the random_z_angle lines if you still want random rotation on top of the slot)
        
        # random_z_angle = random.uniform(0, 360)
        # quat = euler_angles_to_quat(np.array([0, 0, random_z_angle]), degrees=True)
        quat = np.array([1.0, 0.0, 0.0, 0.0]) # Identity quaternion
        
        item_prim.set_local_pose(
            translation=np.array([0.0, 0.0, 0.0]), 
            orientation=quat
        )
        
        instance_counter += 1

    print(f"🚀 Successfully spawned {instance_counter} random items into slots!")

# Execute the function
populate_slots_with_random_items()

