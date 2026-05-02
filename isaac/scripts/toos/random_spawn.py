import random
import numpy as np
import omni.usd
from omni.isaac.core.utils.prims import get_prim_at_path, delete_prim, is_prim_path_valid
from omni.isaac.core.prims import XFormPrim
from omni.isaac.core.utils.rotations import euler_angles_to_quat
import omni.kit.commands

# 1. 환경 기본 설정
STAGE = omni.usd.get_context().get_stage()
CANDIDATES_PATH = "/World/Candidates"
INSTANCES_GROUP_PATH = "/World/Instances"

# 10x10 플레인 범위
SPAWN_AREA_MIN = -5.0
SPAWN_AREA_MAX = 5.0

def generate_random_scene():
    # --- [초기화 단계] 이전 인스턴스 싹 지우기 ---
    # 유니티의 Find + Destroy 과정입니다.
    if is_prim_path_valid(INSTANCES_GROUP_PATH):
        print(f"🧹 기존 인스턴스 초기화 중: {INSTANCES_GROUP_PATH}")
        delete_prim(INSTANCES_GROUP_PATH)
    
    # 인스턴스들을 담을 깨끗한 빈 폴더(Xform) 생성
    omni.kit.commands.execute('CreatePrim', prim_type='Xform', prim_path=INSTANCES_GROUP_PATH)

    # --- [1단계] Candidate Prims 접근 ---
    candidates_prim = STAGE.GetPrimAtPath(CANDIDATES_PATH)
    if not candidates_prim or not candidates_prim.IsValid():
        print(f"❌ 템플릿 경로를 찾을 수 없습니다: {CANDIDATES_PATH}")
        return

    templates = candidates_prim.GetChildren()
    instance_counter = 0

    # --- [2, 3단계] 랜덤 카운트 인스턴싱 및 배치 ---
    for template in templates:
        template_path = str(template.GetPath())
        random_count = random.randint(1, 4) # 오브젝트당 1~4개 랜덤 생성
        
        for _ in range(random_count):
            new_path = f"{INSTANCES_GROUP_PATH}/Item_{instance_counter:03d}"
            
            # 스테이지 내부 복제 (0,0,-10의 원본을 가져옴)
            omni.kit.commands.execute('CopyPrims',
                paths_from=[template_path],
                paths_to=[new_path]
            )
            
            # 위치 및 회전 설정
            pos = np.array([
                random.uniform(SPAWN_AREA_MIN, SPAWN_AREA_MAX),
                random.uniform(SPAWN_AREA_MIN, SPAWN_AREA_MAX),
                0.01 # 바닥(0)에 최대한 가깝게 5cm만 띄움
            ])
            
            # 4.5.0 버전용 euler_angles_to_quat
            random_z_angle = random.uniform(0, 360)
            quat = euler_angles_to_quat(np.array([0, 0, random_z_angle]), degrees=True)
            
            # XFormPrim을 사용하여 확실하게 0,0,-10에서 탈출시킴
            item_prim = XFormPrim(prim_path=new_path)
            item_prim.set_world_pose(position=pos, orientation=quat)
            
            instance_counter += 1

    print(f"🚀 초기화 완료 및 {instance_counter}개의 새 물체 배치 완료!")

# 실행
generate_random_scene()


