import omni.replicator.core as rep
import omni.isaac.core.utils.prims as prim_utils

class CameraManager:
    def __init__(self, camera_path: str):
        self.camera_path = camera_path
        self.rp = None

    def on_simulation_start(self):
        if not prim_utils.is_prim_path_valid(self.camera_path):
            print(f"❌ Error: Camera path '{self.camera_path}' is NOT valid!")
            return

        self.rp = rep.create.render_product(self.camera_path, resolution=(640, 480))
        rep.orchestrator.step()
        print(f"✅ Render Product Created for: {self.camera_path}")

    def on_simulation_end(self):
        if self.rp:
            self.rp.destroy()
            self.rp = None
            print("Render Product Destroyed Successfully")