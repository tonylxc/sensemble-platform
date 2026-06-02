"""数据质量评分 DQS v1（三维加权：完整度 / 元数据完整度 / 异常值比例）。

DQS = (0.45*完整度 + 0.30*元数据完整度 + 0.25*(1-异常率)) * 100
分级：A>=85, B>=70, C>=60, 否则 D（<60 视为较差）。
"""
import numpy as np

REQUIRED_META = ["sensor_type", "accuracy", "sample_interval", "location", "calibration_date"]
W = {"completeness": 0.45, "metadata": 0.30, "anomaly": 0.25}


def completeness(actual: int, expected: int) -> float:
    return 0.0 if expected <= 0 else min(1.0, actual / expected)


def metadata_completeness(meta: dict) -> float:
    if not meta:
        return 0.0
    return sum(1 for k in REQUIRED_META if meta.get(k)) / len(REQUIRED_META)


def anomaly_rate(values: list[float]) -> float:
    arr = np.asarray([v for v in values if v is not None], dtype=float)
    if arr.size < 5:
        return 0.0
    mu, sd = float(arr.mean()), float(arr.std())
    if sd == 0:
        return 0.0
    z = np.abs((arr - mu) / sd)
    return float((z > 3).sum()) / arr.size


def grade(score: float) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 60:
        return "C"
    return "D"


def compute(actual: int, expected: int, meta: dict, values: list[float]):
    c = completeness(actual, expected)
    m = metadata_completeness(meta)
    a = anomaly_rate(values)
    score = round((W["completeness"] * c + W["metadata"] * m + W["anomaly"] * (1 - a)) * 100, 1)
    detail = {"completeness": round(c, 3), "metadata": round(m, 3),
              "anomaly_rate": round(a, 3), "weights": W}
    return score, grade(score), detail


# ===== DQS 完整版（五维，FR-6.2）=====
WF = {"completeness": 0.30, "continuity": 0.25, "metadata": 0.20,
      "calibration": 0.10, "anomaly": 0.15}


def time_continuity(timestamps, interval_s: float = 60) -> float:
    """时序连续性：相邻采样间隔 ≤ 1.5×采样周期 视为连续。"""
    ts = sorted(t for t in timestamps if t is not None)
    if len(ts) < 2:
        return 1.0
    tol = max(1.0, interval_s * 1.5)
    good = sum(1 for a, b in zip(ts, ts[1:]) if (b - a).total_seconds() <= tol)
    return good / (len(ts) - 1)


def calibration_score(meta: dict) -> float:
    """校准/精度说明完整度：accuracy 与 calibration_date 各 0.5。"""
    if not meta:
        return 0.0
    return (0.5 if meta.get("accuracy") else 0.0) + (0.5 if meta.get("calibration_date") else 0.0)


def compute_full(actual: int, expected: int, meta: dict, values: list,
                 timestamps: list, interval_s: float = 60):
    c = completeness(actual, expected)
    cont = time_continuity(timestamps, interval_s)
    m = metadata_completeness(meta)
    cal = calibration_score(meta)
    a = anomaly_rate(values)
    score = round((WF["completeness"] * c + WF["continuity"] * cont + WF["metadata"] * m
                   + WF["calibration"] * cal + WF["anomaly"] * (1 - a)) * 100, 1)
    detail = {"completeness": round(c, 3), "continuity": round(cont, 3),
              "metadata": round(m, 3), "calibration": round(cal, 3),
              "anomaly_rate": round(a, 3), "weights": WF, "version": "v2-5dim"}
    return score, grade(score), detail
