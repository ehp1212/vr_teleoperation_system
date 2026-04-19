from pxr import Usd
import omni.usd

stage = omni.usd.get_context().get_stage()

camera_path = "/World/Camera"

print("=== Render Products for Camera ===")

for prim in stage.Traverse():
    if prim.GetTypeName() == "RenderProduct":
        rel = prim.GetRelationship("camera")
        if rel:
            targets = rel.GetTargets()
            for t in targets:
                if str(t) == camera_path:
                    print("Found:", prim.GetPath())
