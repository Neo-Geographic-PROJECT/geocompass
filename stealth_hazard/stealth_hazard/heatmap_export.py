"""解析結果のエクスポート。

将来的な3Dモデリング工程（第5章）でヒートマップをデカール／テクスチャとして
地形の起伏にUVマッピングする想定のため、ここでは以下2形式で書き出す。

1. CSV  … GISへの再取り込み・数値検証用
2. PPM  … 依存パッケージなしで確認できる簡易グレースケールヒートマップ

本番では rasterio / Pillow 等を用いて GeoTIFF・PNG を直接出力する
（README.md §6 参照）。
"""

from __future__ import annotations

import csv


def export_csv(results: list, path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "row0", "col0", "row1", "col1",
                "max_elev", "min_elev", "relief",
                "mean_slope_deg", "cliff_length_m", "index",
            ]
        )
        for r in results:
            writer.writerow(
                [
                    r.row0, r.col0, r.row1, r.col1,
                    r.max_elev, r.min_elev, r.relief,
                    r.mean_slope_deg, r.cliff_length_m, r.index,
                ]
            )


def _index_to_gray(value: float, vmax: float) -> int:
    if vmax <= 0:
        return 0
    ratio = max(0.0, min(1.0, value / vmax))
    return round(ratio * 255)


def export_heatmap_ppm(results: list, span: int, path: str) -> None:
    """マイメッシュ単位の指数をグレースケールPPM(P3, ASCII)として書き出す。

    span は windowed_analysis.cells_per_window() の戻り値（ウィンドウの一辺のセル数）。
    """
    if not results:
        raise ValueError("resultsが空です")

    grid_rows = max(r.row0 for r in results) // span + 1
    grid_cols = max(r.col0 for r in results) // span + 1
    grid = [[0.0] * grid_cols for _ in range(grid_rows)]
    for r in results:
        grid[r.row0 // span][r.col0 // span] = r.index

    vmax = max(v for row in grid for v in row)

    with open(path, "w", encoding="ascii") as f:
        f.write(f"P3\n{grid_cols} {grid_rows}\n255\n")
        for row in grid:
            for v in row:
                gray = _index_to_gray(v, vmax)
                f.write(f"{gray} {gray} {gray}\n")
