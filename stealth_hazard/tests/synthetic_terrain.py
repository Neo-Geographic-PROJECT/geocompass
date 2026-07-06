"""ユニットテスト用の合成DEM生成。

実データ（基盤地図情報DEM5A）を用意せずに、アルゴリズムの正しさと
研究仮説（平均斜度だけでは検出できないハザードを本指数が検出できること）
を数値的に検証するための最小限の地形パターンを生成する。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stealth_hazard.dem_grid import DemGrid  # noqa: E402


def flat(rows: int, cols: int, resolution_m: float = 5.0, elev: float = 100.0) -> DemGrid:
    """完全な平地。崖なし・斜度0。"""
    return DemGrid(elevations=[[elev] * cols for _ in range(rows)], resolution_m=resolution_m)


def uniform_slope(
    rows: int, cols: int, resolution_m: float = 5.0, base: float = 100.0, rise_per_cell: float = 0.5
) -> DemGrid:
    """X方向に一定勾配で単調に上昇する地形。崖は含まない（隣接セル間の傾きが閾値未満）。"""
    elevations = [[base + rise_per_cell * c for c in range(cols)] for _ in range(rows)]
    return DemGrid(elevations=elevations, resolution_m=resolution_m)


def hidden_cliff(
    rows: int,
    cols: int,
    resolution_m: float = 5.0,
    base: float = 100.0,
    drop_m: float = 11.0,
    cliff_row: int | None = None,
) -> DemGrid:
    """全体としては平坦に近いが、ある行の境界で一段だけ切り立った崖を持つ地形。

    「道路等にカモフラージュされた微細地形リスク」の最小モデル。
    drop_m=11.0, resolution_m=5.0 の場合、崖エッジの斜度は
    atan(11/5) ≈ 65.6° となり、既定の崖判定閾値（約63.4°）を上回る。
    """
    if cliff_row is None:
        cliff_row = rows // 2
    elevations = [
        [base if r < cliff_row else base - drop_m for c in range(cols)] for r in range(rows)
    ]
    return DemGrid(elevations=elevations, resolution_m=resolution_m)


def rocky_peak(
    rows: int, cols: int, resolution_m: float = 5.0, base: float = 100.0, peak_height: float = 60.0
) -> DemGrid:
    """西上州の岩峰を模した、全体的に急峻で崖も多い地形（「あからさまな危険」の対比用）。"""
    cr, cc = rows / 2, cols / 2
    max_dist = max(cr, cc)
    elevations = []
    for r in range(rows):
        row = []
        for c in range(cols):
            dist = ((r - cr) ** 2 + (c - cc) ** 2) ** 0.5
            row.append(base + peak_height * max(0.0, 1.0 - dist / max_dist) ** 0.3)
        elevations.append(row)
    return DemGrid(elevations=elevations, resolution_m=resolution_m)
