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
# stage 분리
# =========================
capture_df = ros_df[ros_df["stage"] == "capture"].copy()
render_df = unity_df[unity_df["stage"] == "render"].copy()

# timestamp 이름 분리
capture_df = capture_df.rename(columns={"ts": "ts_capture"})
render_df = render_df.rename(columns={"ts": "ts_render"})

capture_df = capture_df.sort_values("ts_capture")
render_df = render_df.sort_values("ts_render")

print("Capture:", len(capture_df))
print("Render:", len(render_df))

# =========================
# timestamp 기반 매칭
# =========================
merged = pd.merge_asof(
    render_df,
    capture_df,
    left_on="ts_render",
    right_on="ts_capture",
    direction="nearest"
)

print("Matched:", len(merged))

# =========================
# Latency 계산 (Relative)
# =========================
merged["latency"] = merged["ts_render"] - merged["ts_capture"]

# clock offset 제거
merged["latency"] -= merged["latency"].min()

merged["latency_ms"] = merged["latency"] * 1000

# =========================
# Jitter
# =========================
merged["jitter_ms"] = merged["latency_ms"].diff().abs()

# =========================
# FPS (Unity 기준)
# =========================
render_df["delta"] = render_df["ts_render"].diff()
render_df["fps"] = 1.0 / render_df["delta"]

# =========================
# 통계 출력
# =========================
print("\n=== Relative Latency ===")
print("Mean (ms):", merged["latency_ms"].mean())
print("Max (ms):", merged["latency_ms"].max())

print("\n=== Jitter ===")
print("Mean (ms):", merged["jitter_ms"].mean())

print("\n=== FPS ===")
print("Mean:", render_df["fps"].mean())

# =========================
# 🔥 핵심: Subplot (한 화면)
# =========================
fig, axs = plt.subplots(3, 1, figsize=(10, 10))

# 1️⃣ Latency
axs[0].plot(merged["ts_render"].to_numpy(), merged["latency_ms"].to_numpy())
axs[0].set_title("Relative End-to-End Latency")
axs[0].set_ylabel("Latency (ms)")

# 2️⃣ Jitter
axs[1].plot(merged["ts_render"].to_numpy(), merged["jitter_ms"].to_numpy())
axs[1].set_title("Jitter")
axs[1].set_ylabel("Jitter (ms)")

# 3️⃣ FPS
axs[2].plot(render_df["ts_render"].to_numpy(), render_df["fps"].to_numpy())
axs[2].set_title("Render FPS")
axs[2].set_ylabel("FPS")
axs[2].set_xlabel("Time")

plt.tight_layout()
plt.show()