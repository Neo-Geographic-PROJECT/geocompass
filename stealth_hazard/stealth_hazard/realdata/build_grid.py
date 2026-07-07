"""GMLタイル群（緯度経度・不定形カバレッジ）から、DemGridが要求する
「真に等方な5m格子」を構築するパイプライン。

DEM5Aは0.2秒×0.2秒の経緯度格子であり、南北方向は緯度によらず約6.2m、
東西方向は緯度が高いほど短くなる（例: 東京付近で約5.1m）— 国土地理院公式
FAQ Q.4-2で明記の通り、そもそも等方な5m格子ではない。cliff.pyの崖判定閾値
atan(2.0)≈63.4°は「隣接セル間隔5m」を前提にした式のため、実データを
そのままCSV化すると閾値の意味が変わってしまう。そのため、

  1. 各タイルの構成点を緯度経度からJGD2011平面直角座標系（メートル）へ再投影
  2. 再投影後の点群を、真に5.0m間隔の格子へ最近傍法でリサンプリング
     （線形補間は崖のエッジをなましてしまい、本研究が検出対象とする
     ステルスハザードそのものを消してしまうため、意図的に最近傍法を使う）
  3. 海岸線・選択範囲の外形は矩形にならないため、捏造データを含まないよう
     最大連結成分の中から「全セルが実測値である最大の軸並行矩形」を抽出する
     （小さな穴だけは近傍値で補完し、大きな未選択領域は補完せず除外する）

という手順を踏む。JGD2024とJGD2011の水平方向の差は関東・群馬エリアで
cmオーダーのため、無視して差し支えない前提でEPSG:6668(JGD2011 lat/lon)を使う。
"""
from __future__ import annotations

import glob
import sys

import numpy as np
from pyproj import Transformer
from scipy import ndimage
from scipy.spatial import cKDTree

from stealth_hazard.dem_grid import DemGrid

from .gml_parser import parse_gml_dem_tile

RESOLUTION_M = 5.0
EPSG_LATLON = "EPSG:6668"  # JGD2011 (B, L) — JGD2024との差は本研究の精度要求に対し無視できる
EPSG_PLANE_IX = "EPSG:6677"  # JGD2011 / 平面直角座標系IX系（関東・群馬・神奈川など）


def load_points(gml_glob: str, progress: bool = True):
    """globパターンに一致する全GMLタイルを読み込み、(lat, lon, elev) を結合して返す。"""
    files = sorted(glob.glob(gml_glob))
    if not files:
        raise FileNotFoundError(f"GMLファイルが見つかりません: {gml_glob}")
    lats, lons, elevs = [], [], []
    for i, f in enumerate(files):
        res = parse_gml_dem_tile(f)
        if res is None or len(res[2]) == 0:
            continue
        lat, lon, elev = res
        lats.append(lat)
        lons.append(lon)
        elevs.append(elev)
        if progress and (i + 1) % 100 == 0:
            print(f"  parsed {i+1}/{len(files)} tiles", file=sys.stderr)
    return np.concatenate(lats), np.concatenate(lons), np.concatenate(elevs)


def reproject_to_plane(lat, lon, epsg_plane: str = EPSG_PLANE_IX):
    transformer = Transformer.from_crs(EPSG_LATLON, epsg_plane, always_xy=True)
    x, y = transformer.transform(lon, lat)
    return x, y


def resample_to_isotropic_grid(x, y, elev, resolution_m: float = RESOLUTION_M):
    """散布点群を真に等方な resolution_m 間隔の格子へ最近傍法でリサンプリングする。

    行0=北、列0=西（stealth_hazard.dem_grid.DemGridの想定と同じ並び）。
    最近傍点までの距離が resolution_m の1.5倍を超えるセルはnodata(nan)のままとする。
    """
    x0, x1 = x.min(), x.max()
    y0, y1 = y.min(), y.max()
    ncols = int(np.floor((x1 - x0) / resolution_m)) + 1
    nrows = int(np.floor((y1 - y0) / resolution_m)) + 1

    tree = cKDTree(np.column_stack([x, y]))
    gx = x0 + (np.arange(ncols) + 0.5) * resolution_m
    gy = y1 - (np.arange(nrows) + 0.5) * resolution_m
    gxx, gyy = np.meshgrid(gx, gy)
    query = np.column_stack([gxx.ravel(), gyy.ravel()])

    dist, nn_idx = tree.query(query, k=1, workers=-1)
    grid = elev[nn_idx].reshape(nrows, ncols)
    grid[dist.reshape(nrows, ncols) > resolution_m * 1.5] = np.nan
    return grid


def _largest_all_valid_rectangle(mask: np.ndarray):
    """maskの中で全セルが有効(True)な最大面積の軸並行矩形を (row0,row1,col0,col1) で返す。

    「ヒストグラム中の最大長方形」アルゴリズムを行ごとに適用するO(rows*cols)手法。
    """
    nrows, ncols = mask.shape
    height = np.zeros(ncols, dtype=np.int32)
    best = (0, 0, 0, 0, 0)  # area, r0, r1, c0, c1
    for r in range(nrows):
        height = np.where(mask[r], height + 1, 0)
        stack = []
        for c in range(ncols + 1):
            h = height[c] if c < ncols else 0
            start = c
            while stack and stack[-1][1] >= h:
                start, sh = stack[-1]
                stack.pop()
                area = sh * (c - start)
                if area > best[0]:
                    best = (area, r - sh + 1, r, start, c - 1)
            stack.append((start, h))
    _, r0, r1, c0, c1 = best
    return r0, r1, c0, c1


def crop_to_real_data_only(grid: np.ndarray, min_hole_fill_cells: int = 25):
    """調査対象外領域（海・未選択域）を捏造せず、実測値のみの最大矩形を切り出す。"""
    mask = ~np.isnan(grid)
    labeled, n = ndimage.label(mask)
    if n == 0:
        raise ValueError("有効なDEMセルが1つもありません")
    sizes = ndimage.sum(mask, labeled, range(1, n + 1))
    largest = np.argmax(sizes) + 1
    comp_mask = labeled == largest
    rows, cols = np.where(comp_mask)
    r0, r1, c0, c1 = rows.min(), rows.max(), cols.min(), cols.max()

    sub = np.where(comp_mask[r0:r1 + 1, c0:c1 + 1], grid[r0:r1 + 1, c0:c1 + 1], np.nan)

    # 連結成分内部の小さな穴（浅い水面のGML欠測点など）だけを最近傍値で埋める
    hole_mask = np.isnan(sub)
    hole_labeled, hole_n = ndimage.label(hole_mask)
    if hole_n:
        hole_sizes = ndimage.sum(hole_mask, hole_labeled, range(1, hole_n + 1))
        fillable = np.isin(hole_labeled, [i + 1 for i, s in enumerate(hole_sizes) if s <= min_hole_fill_cells])
        if fillable.any():
            valid_rc = np.column_stack(np.where(~np.isnan(sub)))
            tree = cKDTree(valid_rc)
            nan_rc = np.column_stack(np.where(fillable))
            _, idx = tree.query(nan_rc, k=1)
            sub[nan_rc[:, 0], nan_rc[:, 1]] = sub[valid_rc[idx, 0], valid_rc[idx, 1]]

    still_valid = ~np.isnan(sub)
    rr0, rr1, cc0, cc1 = _largest_all_valid_rectangle(still_valid)
    return sub[rr0:rr1 + 1, cc0:cc1 + 1]


def build_dem_grid_from_gml(gml_glob: str, resolution_m: float = RESOLUTION_M, progress: bool = True) -> DemGrid:
    """GMLタイル群から、DemGrid.from_csv()相当の等方grid・実測値のみのDemGridを構築する。"""
    lat, lon, elev = load_points(gml_glob, progress=progress)
    x, y = reproject_to_plane(lat, lon)
    grid = resample_to_isotropic_grid(x, y, elev, resolution_m)
    grid = crop_to_real_data_only(grid)
    return DemGrid(elevations=grid.tolist(), resolution_m=resolution_m)
