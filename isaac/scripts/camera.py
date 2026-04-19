import omni.replicator.core as rep

class IsaacCamera:
    def __init__(self):

        # ⭐ 기존 카메라 사용 (경로 문자열)
        self.render_product = rep.create.render_product(
            "/World/Camera", (640, 480)
        )

        # ⭐ Annotator
        self.annotator = rep.AnnotatorRegistry.get_annotator("rgb")
        self.annotator.attach(self.render_product)

    def get_frame(self):
        data = self.annotator.get_data()

        if data is None:
            return None

        return data[:, :, :3]