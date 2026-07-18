"""マイメッシュ（ウィンドウ）単位の地形解析。

指定したウィンドウサイズ（例: 50m, 20m, 10m四方）でDEMを分割し、
各ウィンドウの最高・最低標高、比高、平均斜度、崖延長合算、
および難易度指数を集計する。
"""

from __future__ import annotations

from dataclasses import dataclass

from .cliff import DEFAULT_CLIFF_SLOPE_DEG, cliff_edges
from .dem_grid import DemGrid
from .index import difficulty_index
from .slope import compute_slope_grid


@dataclass
class WindowResult:
    row0: int
    col0: int
    row1: int
    col1: int
    max_elev: float
    min_elev: float
    relief: float
    mean_slope_deg: float
    cliff_length_m: float
    index: float


def cells_per_window(dem: DemGrid, window_m: float) -> int:
    return max(1, round(window_m / dem.resolution_m))


def analyze(
    dem: DemGrid,
    window_m: float,
    cliff_slope_threshold_deg: float = DEFAULT_CLIFF_SLOPE_DEG,
) -> list:
    """DEM全体を window_m 四方のマイメッシュに分割して解析する。

    崖エッジは、その始点セル（右方向・下方向エッジの左上側の端点）が
    属するウィンドウに帰属させる簡易的な按分ルールを採用している
    （厳密な按分は本番のGeoTIFF移行時に rasterio.windows で対応する）。
    """
    span = cells_per_window(dem, window_m)
    slope_grid = compute_slope_grid(dem)
    edges = cliff_edges(dem, cliff_slope_threshold_deg)

    results = []
    for r0 in range(0, dem.height, span):
        r1 = min(r0 + span, dem.height)
        for c0 in range(0, dem.width, span):
            c1 = min(c0 + span, dem.width)

            elevs = [dem.get(r, c) for r in range(r0, r1) for c in range(c0, c1)]
            slopes = [slope_grid[r][c] for r in range(r0, r1) for c in range(c0, c1)]
            max_elev = max(elevs)
            min_elev = min(elevs)
            mean_slope = sum(slopes) / len(slopes)

            cliff_length = sum(
                length
                for (ra, ca, _rb, _cb, length) in edges
                if r0 <= ra < r1 and c0 <= ca < c1
            )

            results.append(
                WindowResult(
                    row0=r0,
                    col0=c0,
                    row1=r1,
                    col1=c1,
                    max_elev=max_elev,
                    min_elev=min_elev,
                    relief=max_elev - min_elev,
                    mean_slope_deg=mean_slope,
                    cliff_length_m=cliff_length,
                    index=difficulty_index(cliff_length, mean_slope),
                )
            )
    return results
