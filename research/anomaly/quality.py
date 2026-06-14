"""数据质量门控（创新点1的核心）。

从数据本身提取可解释的质量风险特征，得到逐点/逐通道质量风险 r∈[0,1] 与门控 g=1-r：
- flatline/掉线：通道滚动标准差≈0，或原始 NaN
- drift/漂移   ：通道滚动均值的局部斜率偏大
- saturation/饱和量化：窗口内唯一值比例过低

通道级 r_{t,c} 用于「通道门控」：只打压被质量问题解释的通道，避免误伤其他通道的真异常。
门控不"偷看"注入位置，仅依据数据质量签名——这正是方法的可迁移之处。
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def quality_risk_channels(X_raw: np.ndarray, w: int = 25) -> np.ndarray:
    """逐通道质量风险 r_{t,c}∈[0,1]，形状 (T,C)。X_raw 为含 NaN 的原始观测（未插补）。"""
    df = pd.DataFrame(X_raw)
    col_std = np.nanstd(X_raw, axis=0, keepdims=True) + 1e-9          # (1,C)

    # 1) flatline：滚动标准差≈0（含算不出 → 全 NaN 窗口）
    roll_std = df.rolling(w, min_periods=3, center=True).std().to_numpy()
    flat = (roll_std < 0.05 * col_std).astype(float)
    flat = np.where(np.isnan(roll_std), 1.0, flat)

    # 2) drift：滚动均值的局部斜率（按通道尺度归一）
    roll_mean = df.rolling(w, min_periods=3, center=True).mean().to_numpy()
    slope = np.abs(np.gradient(np.nan_to_num(roll_mean), axis=0))
    drift = np.clip(slope / (col_std / w + 1e-9) / 3.0, 0.0, 1.0)

    # 3) saturation/quantization：窗口内唯一值比例低
    def _uniq_ratio(a):
        a = a[~np.isnan(a)]
        return (len(np.unique(np.round(a, 3))) / len(a)) if len(a) else 1.0
    uniq = df.rolling(w, min_periods=3, center=True).apply(_uniq_ratio, raw=True).to_numpy()
    sat = np.nan_to_num(np.clip(1.0 - uniq / 0.5, 0.0, 1.0), nan=0.0)

    # 4) 原始缺失
    miss = np.isnan(X_raw).astype(float)

    return np.clip(np.maximum.reduce([flat, drift, sat, miss]), 0.0, 1.0)   # (T,C)


def quality_risk(X_raw: np.ndarray, w: int = 25) -> np.ndarray:
    """逐点（跨通道聚合）质量风险 r_t∈[0,1]。"""
    cr = quality_risk_channels(X_raw, w)
    r = pd.Series(cr.max(axis=1)).rolling(5, min_periods=1, center=True).max().to_numpy()
    return np.clip(r, 0.0, 1.0)


def quality_gate(X_raw: np.ndarray, w: int = 25):
    """逐点门控 (g_t, r_t)：g=1-r。"""
    r = quality_risk(X_raw, w)
    return 1.0 - r, r
