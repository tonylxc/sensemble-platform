"""合成多元时序 + 真异常/质量异常注入；以及 SMD 公开数据集加载接口。

对应选题论证 §3（方法与技术路线 / 实验设计）：
- 真异常 (true anomaly)：多通道一致的系统级突变(阶跃/尖峰)，是要检出的目标。
- 质量异常 (quality anomaly)：单通道数据质量伪迹(掉线/漂移/饱和量化)，不应判为系统异常。

合成可控注入让我们能在「已知标签」上定量验证：质量门控是否能在不伤真异常召回的
前提下压低质量误报（这也是论证里写明的可解释性/风险定量验证方式）。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

import numpy as np


@dataclass
class Segment:
    start: int
    end: int
    channels: Tuple[int, ...]
    kind: str  # 'true' | 'dropout' | 'drift' | 'saturation'


@dataclass
class SyntheticData:
    X: np.ndarray        # (T, C) 观测（含质量伪迹，dropout 处为 NaN）
    y_true: np.ndarray   # (T,) 真异常逐点标签
    y_qual: np.ndarray   # (T,) 质量异常逐点标签
    segments: List[Segment]
    clean: np.ndarray    # (T, C) 注入前的干净信号（参考）


def make_synthetic(T: int = 6000, C: int = 10, period: int = 144, seed: int = 0,
                   n_true: int = 6, n_qual: int = 12) -> SyntheticData:
    """生成带季节性与跨通道相关噪声的多元时序，并注入两类异常。"""
    rng = np.random.default_rng(seed)
    t = np.arange(T)

    # 基信号：季节性 + 跨通道相关的 AR(1) 噪声
    phase = rng.uniform(0, 2 * np.pi, C)
    amp = rng.uniform(0.5, 1.5, C)
    season = amp * np.sin(2 * np.pi * t[:, None] / period + phase)

    mix = np.tril(rng.normal(0, 1, (C, C)))           # 下三角混合矩阵 → 通道相关
    innov = rng.normal(0, 0.3, (T, C)) @ mix.T
    noise = np.zeros((T, C))
    rho = 0.6
    for i in range(1, T):
        noise[i] = rho * noise[i - 1] + innov[i]

    clean = season + noise
    X = clean.copy()
    y_true = np.zeros(T, dtype=int)
    y_qual = np.zeros(T, dtype=int)
    segs: List[Segment] = []

    # 真异常：多通道一致的阶跃
    for _ in range(n_true):
        length = int(rng.integers(30, 80))
        s = int(rng.integers(period, T - length))
        k = int(rng.integers(max(2, C // 2), C + 1))
        ch = tuple(sorted(int(x) for x in rng.choice(C, size=k, replace=False)))
        mag = float(rng.choice([-1.0, 1.0]) * rng.uniform(3.0, 5.0))
        X[s:s + length][:, ch] += mag
        y_true[s:s + length] = 1
        segs.append(Segment(s, s + length, ch, 'true'))

    # 质量异常：单通道数据伪迹
    kinds = ('dropout', 'drift', 'saturation')
    for _ in range(n_qual):
        length = int(rng.integers(40, 120))
        s = int(rng.integers(period, T - length))
        ch = int(rng.integers(0, C))
        kind = kinds[int(rng.integers(0, len(kinds)))]
        if kind == 'dropout':                          # 掉线 → NaN（入库前按保持/插补处理）
            X[s:s + length, ch] = np.nan
        elif kind == 'drift':                          # 缓慢漂移（未校准）
            X[s:s + length, ch] = clean[s:s + length, ch] + np.linspace(0, rng.uniform(3, 6), length)
        else:                                          # 饱和 + 量化
            cap = np.nanpercentile(clean[:, ch], 85)
            seg = np.minimum(clean[s:s + length, ch], cap)
            X[s:s + length, ch] = np.round(seg * 2) / 2
        y_qual[s:s + length] = 1
        segs.append(Segment(s, s + length, (ch,), kind))

    return SyntheticData(X=X, y_true=y_true, y_qual=y_qual, segments=segs, clean=clean)


def impute(X: np.ndarray) -> np.ndarray:
    """前向填充 NaN（模拟入库前的简单插补）；起始残留用 0。

    注意：dropout 经插补后表现为「平直段」，朴素检测器仍会因其偏离季节性而误报——
    这正是质量门控要识别并抑制的情形。
    """
    X = X.copy()
    for c in range(X.shape[1]):
        col = X[:, c]
        last = 0.0
        seen = False
        for i in range(len(col)):
            if np.isnan(col[i]):
                col[i] = last if seen else 0.0
            else:
                last = col[i]
                seen = True
        X[:, c] = col
    return X


def load_smd(root: str, machine: str = "machine-1-1"):
    """加载 SMD（Server Machine Dataset）一台机器的 train/test/label。

    数据获取：OmniAnomaly 仓库 ServerMachineDataset/ 下
      train/<machine>.txt, test/<machine>.txt, test_label/<machine>.txt （逗号分隔）
    返回 (X_train, X_test, y_test)。下载后即可把 experiment 的数据源换成它。
    """
    import os
    def _read(sub):
        path = os.path.join(root, sub, f"{machine}.txt")
        return np.loadtxt(path, delimiter=",")
    X_train = _read("train")
    X_test = _read("test")
    y_test = np.loadtxt(os.path.join(root, "test_label", f"{machine}.txt"), delimiter=",").astype(int)
    return X_train, X_test, y_test
