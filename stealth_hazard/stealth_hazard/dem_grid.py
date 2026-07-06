"""DEM（数値標高モデル）の軽量グリッド表現。

本番運用では基盤地図情報DEM5A（GeoTIFF）を rasterio で読み込む想定だが、
依存パッケージなしで動作検証できるよう、ここでは標準ライブラリのみで
完結する2次元配列ベースの実装を提供する。
"""

from __future__ import annotations

import csv
from dataclasses import dataclass


@dataclass
class DemGrid:
    elevations: list  # list[list[float]]  行=Y方向、列=X方向
    resolution_m: float  # セル間隔（例: 5.0m メッシュ）

    @property
    def height(self) -> int:
        return len(self.elevations)

    @property
    def width(self) -> int:
        return len(self.elevations[0]) if self.elevations else 0

    def get(self, row: int, col: int) -> float:
        """範囲外座標は最近傍の端セルにクランプして返す（境界の簡易近似）。"""
        row = min(max(row, 0), self.height - 1)
        col = min(max(col, 0), self.width - 1)
        return self.elevations[row][col]

    @classmethod
    def from_csv(cls, path: str, resolution_m: float) -> "DemGrid":
        """CSV（カンマ区切りの標高値グリッド）からDEMを読み込む。

        本番のDEM5A(GeoTIFF)読み込みは rasterio 導入後に
        from_geotiff() として追加する想定（README.md §6 参照）。
        """
        rows = []
        with open(path, newline="", encoding="utf-8") as f:
            for line in csv.reader(f):
                if not line:
                    continue
                rows.append([float(v) for v in line])
        if not rows:
            raise ValueError(f"DEM CSVが空です: {path}")
        width = len(rows[0])
        if any(len(r) != width for r in rows):
            raise ValueError(f"DEM CSVの各行の列数が揃っていません: {path}")
        return cls(elevations=rows, resolution_m=resolution_m)

    def to_csv(self, path: str) -> None:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in self.elevations:
                writer.writerow(row)
