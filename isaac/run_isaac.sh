#!/bin/bash

echo "🚀 Starting Isaac Sim (clean ROS2 environment)"

# 🔥 기존 ROS 환경 제거 (bashrc 영향 차단)
unset PYTHONPATH
unset LD_LIBRARY_PATH
unset AMENT_PREFIX_PATH
unset COLCON_PREFIX_PATH

unset ROS_DISTRO
unset RMW_IMPLEMENTATION

# ✅ Isaac 내부 ROS 설정
export ROS_DISTRO=humble
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp

ISAAC_PATH=$HOME/isaacsim/_build/linux-x86_64/release

# ❗ 내부 ROS2 lib 경로
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$ISAAC_PATH/exts/isaacsim.ros2.bridge/humble/lib

# 실행
$ISAAC_PATH/python.sh \
$HOME/personal_project/humanoid_digital_twin/isaac/scripts/main.py