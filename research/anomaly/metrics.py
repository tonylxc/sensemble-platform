"""评测指标。

- 真异常排序质量：AUC-PR（阈值无关）
- 等灵敏度质量误报：FAR@full-recall（在"检出全部真异常段"的操作点上比质量误报率）
- 兼容旧接口：point-adjust F1、best_threshold、evaluate
"""
from __future__ import annotations

import numpy as np
from sklearn.metrics import average_precision_score, f1_score, recall_score


def segments(label: np.ndarray):
    """返回标签中连续为 1 的区间列表 [(start, end), ...]（end 不含）。"""
    label = np.asarray(label).astype(int)
    segs, T, i = [], len(label), 0
    while i < T:
        if label[i] == 1:
            j = i
            while j < T and label[j] == 1:
                j += 1
            segs.append((i, j))
            i = j
        else:
            i += 1
    return segs


def point_adjust(pred: np.ndarray, label: np.ndarray) -> np.ndarray:
    """OmniAnomaly 式 point-adjust：真异常段内命中≥1点则整段算命中。"""
    pred = pred.astype(int).copy()
    for s, e in segments(label):
        if pred[s:e].any():
            pred[s:e] = 1
    return pred


def auc_pr(score: np.ndarray, y_true: np.ndarray) -> float:
    return float(average_precision_score(y_true, score)) if y_true.any() else float("nan")


def far_at_full_recall(score: np.ndarray, y_true: np.ndarray, y_qual: np.ndarray):
    """检出全部真异常段（point-adjust 召回=1）所需阈值下的质量误报率。

    阈值 = 各真异常段峰值分数的最小值（保证每段都被命中）；
    返回 (FAR, threshold)。FAR = 质量异常点中分数≥阈值的比例。
    """
    segs = segments(y_true)
    if not segs:
        return float("nan"), float("nan")
    th = min(float(score[s:e].max()) for s, e in segs)
    pred = score >= th
    far = float(pred[y_qual == 1].mean()) if (y_qual == 1).any() else 0.0
    return far, th


def best_threshold(score: np.ndarray, label: np.ndarray, n: int = 200):
    """阈值网格上取 point-adjust F1 最优。返回 (paf1, th)。"""
    ths = np.quantile(score, np.linspace(0.5, 0.999, n))
    best = (0.0, float(ths[-1]))
    for th in ths:
        f = f1_score(label, point_adjust((score >= th).astype(int), label), zero_division=0)
        if f > best[0]:
            best = (f, float(th))
    return best


def evaluate(score: np.ndarray, y_true: np.ndarray, y_qual: np.ndarray, th: float) -> dict:
    pred = (score >= th).astype(int)
    return {
        "PA_F1": f1_score(y_true, point_adjust(pred, y_true), zero_division=0),
        "AUC_PR": auc_pr(score, y_true),
        "recall_true": recall_score(y_true, pred, zero_division=0),
        "qual_FAR": float(pred[y_qual == 1].mean()) if (y_qual == 1).any() else 0.0,
    }
