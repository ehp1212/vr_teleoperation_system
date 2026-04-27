import json
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

# =========================
# 경로 설정
# =========================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "temp_data"

ROS_LOG = DATA_DIR / "ros_log.jsonl"
UNITY_LOG = DATA_DIR / "unity_log.jsonl"

# =========================
# 로그 로드
# =========================
def load_jsonl(path):
    rows = []
    with open(path, "r") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except:
                continue
    return pd.DataFrame(rows)

ros_df = load_jsonl(ROS_LOG)
unity_df = load_jsonl(UNITY_LOG)

print("ROS logs:", len(ros_df))
print("Unity logs:", len(unity_df))

# =========================
# render만 사용 (Unity 기준)
# =========================
render_df = unity_df[unity_df["stage"] == "render"].copy()

render_df = render_df.rename(columns={"ts": "ts_render"})
render_df = render_df.sort_values("ts_render")

print("Render frames:", len(render_df))

# =========================
# Frame interval (핵심)
# =========================
render_df["delta"] = render_df["ts_render"].diff()

# ms 변환
render_df["delta_ms"] = render_df["delta"] * 1000

# FPS
render_df["fps"] = 1.0 / render_df["delta"]

# =========================
# "진짜 jitter" (frame interval 기반)
# =========================
render_df["jitter_ms"] = render_df["delta_ms"].diff().abs()

# =========================
# 통계 출력
# =========================
print("\n=== FPS ===")
print("Mean FPS:", render_df["fps"].mean())

print("\n=== Frame Interval ===")
print("Mean (ms):", render_df["delta_ms"].mean())
print("Max (ms):", render_df["delta_ms"].max())

print("\n=== Jitter ===")
print("Mean (ms):", render_df["jitter_ms"].mean())

# =========================
# 🔥 Subplot (한 화면)
# =========================
fig, axs = plt.subplots(3, 1, figsize=(10, 10))

# 1️⃣ Frame Interval
axs[0].plot(render_df["ts_render"].to_numpy(), render_df["delta_ms"].to_numpy())
axs[0].set_title("Frame Interval (ms)")
axs[0].set_ylabel("ms")

# 2️⃣ Jitter
axs[1].plot(render_df["ts_render"].to_numpy(), render_df["jitter_ms"].to_numpy())
axs[1].set_title("Frame Jitter")
axs[1].set_ylabel("ms")

# 3️⃣ FPS
axs[2].plot(render_df["ts_render"].to_numpy(), render_df["fps"].to_numpy())
axs[2].set_title("Render FPS")
axs[2].set_ylabel("FPS")
axs[2].set_xlabel("Time")

plt.tight_layout()
plt.show()