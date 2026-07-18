"""windowed_analysis.analyze() のnumpyベクトル化版（実データの大規模グリッド向け）。

stealth_hazard.windowed_analysis.analyze() は合成地形での検証を目的とした
意図的な総当たりループ実装であり（README.md §6参照）、実測DEM相当の
セル数（数百万〜数千万）に対しては計算量が非現実的になる。特に
cliff_edges() の結果をウィンドウごとにO(全エッジ数)で再走査する部分が
「ウィンドウ数×エッジ数」のオーダーになり、大きな地域では事実上終わらない。

ここではREADME.md §6が明記する移行方針（DemGrid/WindowResultの
データ構造は変えず内部実装のみnumpyへ置換）に従ってanalyze_np()を実装した。
tests/test_fast_windowed_analysis.py で windowed_analysis.analyze() との
数値的な完全一致（浮動小数点誤差の範囲内）を検証している。
"""
from __future__ import annotations

import numpy as np

from ..cliff import DEFAULT_CLIFF_SLOPE_DEG
from ..dem_grid import DemGrid
from ..index import difficulty_index
from ..windowed_analysis import WindowResult, cells_per_window


def _compute_slope_grid(elev: np.ndarray, resolution_m: float) -> np.ndarray:
    padded = np.pad(elev, 1, mode="edge")
    dzdx = (padded[1:-1, 2:] - padded[1:-1, :-2]) / (2 * resolution_m)
    dzdy = (padded[2:, 1:-1] - padded[:-2, 1:-1]) / (2 * resolution_m)
    grad = np.hypot(dzdx, dzdy)
    return np.degrees(np.arctan(grad))


def _cliff_edge_masks(elev: np.ndarray, resolution_m: float, threshold_deg: float):
    dz_right = np.abs(elev[:, :-1] - elev[:, 1:])
    dz_down = np.abs(elev[:-1, :] - elev[1:, :])
    right = np.degrees(np.arctan(dz_right / resolution_m)) >= threshold_deg
    down = np.degrees(np.arctan(dz_down / resolution_m)) >= threshold_deg
    return right, down  # shape: (rows, cols-1), (rows-1, cols)


def analyze_np(
    dem: DemGrid,
    window_m: float,
    cliff_slope_threshold_deg: float = DEFAULT_CLIFF_SLOPE_DEG,
) -> list:
    elev = np.asarray(dem.elevations, dtype=np.float64)
    resolution_m = dem.resolution_m
    rows, cols = elev.shape
    span = cells_per_window(dem, window_m)

    slope_grid = _compute_slope_grid(elev, resolution_m)
    right_cliff, down_cliff = _cliff_edge_masks(elev, resolution_m, cliff_slope_threshold_deg)

    results = []
    for r0 in range(0, rows, span):
        r1 = min(r0 + span, rows)
        for c0 in range(0, cols, span):
            c1 = min(c0 + span, cols)
            elev_block = elev[r0:r1, c0:c1]
            slope_block = slope_grid[r0:r1, c0:c1]
            max_elev = float(elev_block.max())
            min_elev = float(elev_block.min())
            mean_slope = float(slope_block.mean())

            cliff_len = resolution_m * (
                int(right_cliff[r0:r1, c0:min(c1, cols - 1)].sum())
                + int(down_cliff[r0:min(r1, rows - 1), c0:c1].sum())
            )

            results.append(
                WindowResult(
                    row0=r0, col0=c0, row1=r1, col1=c1,
                    max_elev=max_elev, min_elev=min_elev,
                    relief=max_elev - min_elev,
                    mean_slope_deg=mean_slope,
                    cliff_length_m=cliff_len,
                    index=difficulty_index(cliff_len, mean_slope),
                )
            )
    return results
