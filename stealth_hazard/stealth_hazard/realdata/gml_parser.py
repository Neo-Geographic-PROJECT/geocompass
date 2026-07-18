"""FG-GML DEM5A/5B（基盤地図情報 数値標高モデル、JPGIS2014 GML形式）のタイルパーサー。

基盤地図情報ダウンロードデータファイル仕様書5.2版（3.1節・表2-1・図2-24付近の
sequencingRule/startSequence説明）および国土地理院公式FAQ(Q.4-2/Q.4-4/Q.4-17,
https://www.gsi.go.jp/kiban/faq.html) で確認した規則に基づく:

- grid low=(0,0) は常に北西端セル、high=(224,149)（5mメッシュ）は常に南東端セル
- 走査順序: 北西端起点、+x（西→東）、東端に達すると1行南へ、を南東端まで繰り返す
- startPoint は先頭の欠測（連続するデータなし点）を省略した開始位置。
  末尾の欠測も同様に省略されるため、実際のタプル数だけ前進シミュレーションして
  座標を割り当てる（gridDomainのhighまでデータが必ず届くとは限らない）
- 標高値 -9999 は「種別」ラベルに関わらずnodataとして扱う。GSI公式FAQ Q.4-17の通り、
  内水面は令和5年度の仕様変更以降タイルによって実標高値を持つ場合があるため、
  種別文字列ではなく値そのもので判定する必要がある
"""
from __future__ import annotations

import re

import numpy as np

_HEADER_RE = re.compile(
    r"<gml:lowerCorner>([\d.]+) ([\d.]+)</gml:lowerCorner>\s*"
    r"<gml:upperCorner>([\d.]+) ([\d.]+)</gml:upperCorner>.*?"
    r"<gml:low>(\d+) (\d+)</gml:low>\s*"
    r"<gml:high>(\d+) (\d+)</gml:high>.*?"
    r"<gml:tupleList>(.*?)</gml:tupleList>.*?"
    r"<gml:startPoint>(\d+) (\d+)</gml:startPoint>",
    re.S,
)

NODATA_THRESHOLD = -9000.0


def parse_gml_dem_tile(path: str):
    """1枚のGMLタイルを読み込み、(lat, lon, elev) のnodata除去済みnumpy配列を返す。

    ヘッダー要素が見つからない場合はNoneを返す。
    """
    text = open(path, encoding="utf-8").read()
    m = _HEADER_RE.search(text)
    if not m:
        return None
    lat0, lon0, lat1, lon1, lowx, lowy, highx, highy, tuples, spx, spy = m.groups()
    lat0, lon0, lat1, lon1 = map(float, (lat0, lon0, lat1, lon1))
    lowx, lowy, highx, highy, spx, spy = map(int, (lowx, lowy, highx, highy, spx, spy))
    ncols = highx - lowx + 1
    nrows = highy - lowy + 1
    dlon = (lon1 - lon0) / ncols
    dlat = (lat1 - lat0) / nrows

    lines = [line for line in tuples.strip().split("\n") if line]
    n = len(lines)
    elevs = np.empty(n, dtype=np.float64)
    for i, line in enumerate(lines):
        _kind, val = line.split(",", 1)
        elevs[i] = float(val)

    # startPointから +x（列, ncolsで折り返し）/ 行送り(+row) で前進シミュレーション
    idx = np.arange(n)
    col = spx + idx
    row = spy + (col // ncols)
    col = col % ncols

    valid = elevs > NODATA_THRESHOLD
    lat = lat1 - (row[valid] + 0.5) * dlat
    lon = lon0 + (col[valid] + 0.5) * dlon
    return lat, lon, elevs[valid]
