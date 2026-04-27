from pxr import Usd
import omni.usd

stage = omni.usd.get_context().get_stage()

camera_path = "/World/franka/panda_hand/EE_Camera"

print("=== RenderProduct → Camera mapping ===")

print("=== RenderProduct → Camera mapping ===")

for prim in stage.Traverse():

    if prim.GetTypeName() == "RenderProduct":

        print("RenderProduct:", prim.GetPath())

        rel = prim.GetRelationship("inputs:camera")

        if not rel:
            print("  ❌ No camera linked")
            continue

        targets = rel.GetTargets()

        if not targets:
            print("  ❌ Empty camera target")
            continue

        for t in targets:
            print("  → Camera:", t)

