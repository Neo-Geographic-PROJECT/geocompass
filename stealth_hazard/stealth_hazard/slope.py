"""セル単位の斜度（度）計算。

中心差分（Horn法の簡略版）により、東西南北方向の標高差から
各セルの勾配ベクトルの大きさ（＝斜度）を求める。
"""

from __future__ import annotations

import math

from .dem_grid import DemGrid


def compute_slope_grid(dem: DemGrid) -> list:
    """DEM全セルの斜度（度）を2次元リストで返す。

    境界セルは DemGrid.get() のクランプ処理により端の値を複製して近似する。
    """
    res = dem.resolution_m
    slope = [[0.0] * dem.width for _ in range(dem.height)]
    for r in range(dem.height):
        for c in range(dem.width):
            dzdx = (dem.get(r, c + 1) - dem.get(r, c - 1)) / (2 * res)
            dzdy = (dem.get(r + 1, c) - dem.get(r - 1, c)) / (2 * res)
            grad = math.hypot(dzdx, dzdy)
            slope[r][c] = math.degrees(math.atan(grad))
    return slope
