"""IDW 反距离加权空间插值（FR-7.3）。

给定若干带经纬度的测点，在其包络范围内生成 nx×ny 网格的插值场。
IDW: z(x0) = Σ(w_i·z_i)/Σw_i，w_i = 1/d_i^p（p 默认 2）。结果恒在测值 [min,max] 内。
"""
import numpy as np


def interpolate(points, nx=36, ny=24, power=2.0, pad=0.0008):
    px = np.array([p["lon"] for p in points], dtype=float)
    py = np.array([p["lat"] for p in points], dtype=float)
    pv = np.array([p["value"] for p in points], dtype=float)

    lon0, lon1 = float(px.min()) - pad, float(px.max()) + pad
    lat0, lat1 = float(py.min()) - pad, float(py.max()) + pad
    if lon1 - lon0 < 1e-6:
        lon0 -= 0.001; lon1 += 0.001
    if lat1 - lat0 < 1e-6:
        lat0 -= 0.001; lat1 += 0.001

    lons = np.linspace(lon0, lon1, nx)
    lats = np.linspace(lat0, lat1, ny)
    gx, gy = np.meshgrid(lons, lats)            # (ny, nx)
    GX, GY = gx.ravel(), gy.ravel()

    dx = GX[:, None] - px[None, :]
    dy = GY[:, None] - py[None, :]
    d = np.sqrt(dx * dx + dy * dy)
    w = 1.0 / np.power(d + 1e-9, power)         # +eps 防止 d=0 溢出
    vals = (w * pv[None, :]).sum(1) / w.sum(1)
    vals = vals.reshape(ny, nx)

    cells = [[i, j, round(float(vals[j, i]), 2)] for j in range(ny) for i in range(nx)]

    pts = []
    for p in points:
        i = int(round((p["lon"] - lon0) / (lon1 - lon0) * (nx - 1)))
        j = int(round((p["lat"] - lat0) / (lat1 - lat0) * (ny - 1)))
        pts.append({**p, "i": max(0, min(nx - 1, i)), "j": max(0, min(ny - 1, j))})

    return {
        "nx": nx, "ny": ny, "bbox": [lon0, lat0, lon1, lat1],
        "cells": cells, "points": pts,
        "vmin": round(float(vals.min()), 2), "vmax": round(float(vals.max()), 2),
    }
