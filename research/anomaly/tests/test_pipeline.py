"""把第一篇的核心论断编码成可回归测试。

核心（通道门控 v2）：在"检出全部真异常段"的等灵敏度操作点上显著降低质量误报率，
且不损伤真异常排序质量（AUC-PR）。
"""
import numpy as np

from research.anomaly.datasets import impute, make_synthetic
from research.anomaly.detectors import aggregate, channel_gated, zscore_channels
from research.anomaly.metrics import auc_pr, far_at_full_recall, point_adjust, segments
from research.anomaly.quality import quality_gate, quality_risk_channels


def test_shapes_and_labels():
    d = make_synthetic(T=2000, seed=1)
    assert d.X.shape == (2000, 10)
    assert d.y_true.sum() > 0 and d.y_qual.sum() > 0


def test_imputation_removes_nan():
    d = make_synthetic(T=1500, seed=3)
    assert np.isnan(d.X).any()                 # 注入了掉线
    assert not np.isnan(impute(d.X)).any()


def test_quality_gate_flags_artifacts():
    d = make_synthetic(T=2500, seed=2)
    r = quality_risk_channels(d.X).max(axis=1)
    normal = (d.y_qual == 0) & (d.y_true == 0)
    assert r[d.y_qual == 1].mean() > r[normal].mean() + 0.1


def test_point_adjust_and_segments():
    label = np.array([0, 1, 1, 0, 1, 0])
    assert segments(label) == [(1, 3), (4, 5)]
    pred = np.array([0, 0, 1, 0, 0, 0])        # 命中第一段一点
    assert point_adjust(pred, label).tolist() == [0, 1, 1, 0, 0, 0]


def test_channel_gate_cuts_quality_far_without_hurting_auc():
    base_far, chan_far, base_auc, chan_auc = [], [], [], []
    for seed in range(5):
        d = make_synthetic(T=3000, seed=seed)
        Xim = impute(d.X)
        R = quality_risk_channels(d.X)
        A = zscore_channels(Xim)
        s_base = aggregate(A)
        s_chan = channel_gated(A, R)
        base_far.append(far_at_full_recall(s_base, d.y_true, d.y_qual)[0])
        chan_far.append(far_at_full_recall(s_chan, d.y_true, d.y_qual)[0])
        base_auc.append(auc_pr(s_base, d.y_true))
        chan_auc.append(auc_pr(s_chan, d.y_true))
    # 通道门控显著降低质量误报
    assert np.nanmean(chan_far) < np.nanmean(base_far)
    # 且不损伤真异常排序质量（AUC-PR 不显著变差）
    assert np.mean(chan_auc) >= np.mean(base_auc) - 0.03
