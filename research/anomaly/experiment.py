"""P1 基线实验：无门控 vs 全局门控(v1) vs 通道门控(v2)。

指标：AUC-PR(真异常，越高越好) / FAR@full-recall(检出全部真异常段时的质量误报率，越低越好)
运行：python research/anomaly/experiment.py   或   python -m research.anomaly.experiment
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import numpy as np  # noqa: E402

from research.anomaly.datasets import impute, make_synthetic            # noqa: E402
from research.anomaly.detectors import (aggregate, channel_gated,        # noqa: E402
                                        global_gated, iforest_score,
                                        pca_channels, zscore_channels)
from research.anomaly.metrics import auc_pr, far_at_full_recall          # noqa: E402
from research.anomaly.quality import quality_gate, quality_risk_channels  # noqa: E402

CHANNEL_DETECTORS = {"ZScore": zscore_channels, "PCA-Recon": pca_channels}
GLOBAL_DETECTORS = {"IsolationForest": iforest_score}


def _m(score, d):
    far, _ = far_at_full_recall(score, d.y_true, d.y_qual)
    return {"AUC_PR": auc_pr(score, d.y_true), "FAR_full": far}


def run_once(seed: int):
    d = make_synthetic(seed=seed)
    Xim = impute(d.X)
    g, _ = quality_gate(d.X)
    R = quality_risk_channels(d.X)
    rows = {}
    for name, fn in CHANNEL_DETECTORS.items():
        A = fn(Xim)
        rows[name] = {
            "无门控": _m(aggregate(A), d),
            "全局门控v1": _m(global_gated(A, g), d),
            "通道门控v2": _m(channel_gated(A, R), d),
        }
    for name, fn in GLOBAL_DETECTORS.items():
        s = fn(Xim)
        rows[name] = {"无门控": _m(s, d), "全局门控v1": _m(global_gated(s, g), d)}
    return rows


def main(seeds=range(5)):
    seeds = list(seeds)
    agg = {}
    for sd in seeds:
        for name, variants in run_once(sd).items():
            agg.setdefault(name, {})
            for v, m in variants.items():
                agg[name].setdefault(v, {"AUC_PR": [], "FAR_full": []})
                agg[name][v]["AUC_PR"].append(m["AUC_PR"])
                agg[name][v]["FAR_full"].append(m["FAR_full"])

    print(f"众感 Sensemble · P1 异常检测（合成可控数据，{len(seeds)} 个随机种子平均）")
    print("=" * 68)
    print("指标：AUC-PR(真异常)↑   FAR@full-recall(检出全部真异常段时的质量误报率)↓")
    print("-" * 68)
    print(f"{'检测器':<16}{'门控方案':<14}{'AUC-PR↑':>10}{'FAR@full↓':>12}")
    print("-" * 68)
    for name, variants in agg.items():
        for v, mm in variants.items():
            au = float(np.mean(mm["AUC_PR"]))
            fr = float(np.nanmean(mm["FAR_full"]))
            print(f"{name:<16}{v:<14}{au:>10.3f}{fr:>12.3f}")
        print("-" * 68)
    print("看点：通道门控v2 应在 AUC-PR 不低于无门控的前提下，把 FAR@full 显著压下去；")
    print("      全局门控v1 虽也降 FAR，但会拉低 AUC-PR（误伤真异常）——这正是 v2 的改进点。")


if __name__ == "__main__":
    main()
