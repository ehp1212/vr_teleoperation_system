import omni.replicator.core as rep

# 1. 카메라 경로 설정
camera_path = "/World/franka/panda_hand/EE_Camera"

# 2. Render Product 생성 (해상도 지정 가능)
render_product = rep.create.render_product(camera_path, resolution=(640, 480))

print(f"Render Product created for: {camera_path}")
