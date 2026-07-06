"""崖セル判定と崖延長合算の計算。

2万5千分1地形図における崖記号への置換基準
（0.2mm規定を実距離換算すると、水平5mあたり比高10m以上、
斜度およそ63.4度以上）をデフォルト閾値として、
5mメッシュの隣接セル間の高低差から崖エッジを検出する。

    0.2mm × 25,000 = 5m（水平距離）
    tan(θ) = 10m(比高) / 5m(水平距離) = 2.0  ⇒  θ = atan(2.0) ≈ 63.43°
"""

from __future__ import annotations

import math

from .dem_grid import DemGrid

DEFAULT_CLIFF_SLOPE_DEG = math.degrees(math.atan(2.0))  # 約63.43度


def _edge_slope_deg(dem: DemGrid, r0: int, c0: int, r1: int, c1: int) -> float:
    dz = abs(dem.get(r0, c0) - dem.get(r1, c1))
    dx = dem.resolution_m * math.hypot(r1 - r0, c1 - c0)
    if dx == 0:
        return 0.0
    return math.degrees(math.atan(dz / dx))


def cliff_edges(dem: DemGrid, slope_threshold_deg: float = DEFAULT_CLIFF_SLOPE_DEG) -> list:
    """崖と判定されたエッジ一覧を (r0, c0, r1, c1, length_m) のリストで返す。

    各セルについて「右隣」「下隣」の2方向のみを調べることで、
    同一エッジの二重カウントを防ぐ。
    """
    edges = []
    res = dem.resolution_m
    for r in range(dem.height):
        for c in range(dem.width):
            if c + 1 < dem.width and _edge_slope_deg(dem, r, c, r, c + 1) >= slope_threshold_deg:
                edges.append((r, c, r, c + 1, res))
            if r + 1 < dem.height and _edge_slope_deg(dem, r, c, r + 1, c) >= slope_threshold_deg:
                edges.append((r, c, r + 1, c, res))
    return edges
