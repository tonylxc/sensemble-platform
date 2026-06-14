"""无监督异常检测基线 + 门控聚合。

逐通道异常矩阵 A(T,C)（越大越异常），便于做「通道门控」；以及单分聚合 s_t。
- zscore_channels / pca_channels ：逐通道异常分（支持通道门控）
- iforest_score                  ：多元单分（仅支持全局门控，作对比）
分层路线第一层（统计 + 经典 ML）；深度模型（AE/TCN/Transformer）留作下一刀。
"""
from __future__ import annotations

import numpy as np
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


def _windowize(X: np.ndarray, w: int) -> np.ndarray:
    """以每点为右端构造长度 w 的展平窗口特征；左端用首行填充。返回 (T, w*C)。"""
    T = X.shape[0]
    pad = np.repeat(X[:1], w - 1, axis=0)
    Xp = np.vstack([pad, X])
    return np.stack([Xp[i:i + w].ravel() for i in range(T)])


def _norm(s: np.ndarray) -> np.ndarray:
    s = np.asarray(s, dtype=float)
    lo, hi = np.nanpercentile(s, 1), np.nanpercentile(s, 99)
    return np.clip((s - lo) / (hi - lo + 1e-9), 0.0, 1.0)


# ---- 逐通道异常分 A(T,C) ----
def zscore_channels(X: np.ndarray, w: int = 25) -> np.ndarray:
    import pandas as pd
    df = pd.DataFrame(X)
    mu = df.rolling(w, min_periods=3, center=True).mean()
    sd = df.rolling(w, min_periods=3, center=True).std() + 1e-9
    return ((df - mu) / sd).abs().to_numpy()                # (T,C)


def pca_channels(X: np.ndarray, w: int = 10, n_comp=None) -> np.ndarray:
    C = X.shape[1]
    F = _windowize(StandardScaler().fit_transform(X), w)
    n_comp = n_comp or max(1, min(F.shape[1] // 4, 20))
    pca = PCA(n_components=n_comp).fit(F)
    recon = pca.inverse_transform(pca.transform(F))
    err = ((F - recon) ** 2).reshape(F.shape[0], w, C).mean(axis=1)   # 回摊到通道 (T,C)
    return err


# ---- 多元单分（无通道归因）----
def iforest_score(X: np.ndarray, w: int = 10, seed: int = 0) -> np.ndarray:
    F = _windowize(StandardScaler().fit_transform(X), w)
    model = IsolationForest(n_estimators=150, random_state=seed, contamination="auto")
    model.fit(F)
    return _norm(-model.score_samples(F))


# ---- 聚合策略 ----
def aggregate(A: np.ndarray) -> np.ndarray:
    """无门控基线：逐点取通道最大异常分。"""
    return _norm(np.nanmax(A, axis=1))


def global_gated(A_or_s: np.ndarray, g: np.ndarray) -> np.ndarray:
    """全局门控 v1：g_t · s_t（s 为聚合分或单分）。"""
    s = A_or_s if A_or_s.ndim == 1 else aggregate(A_or_s)
    return _norm(g * s)


def channel_gated(A: np.ndarray, R: np.ndarray) -> np.ndarray:
    """通道门控 v2：max_c (1-r_{t,c})·a_{t,c}，只压被质量问题解释的通道。"""
    return _norm(np.nanmax((1.0 - R) * A, axis=1))
