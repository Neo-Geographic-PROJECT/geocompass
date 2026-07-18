"""地域プリセット（ウィンドウサイズ・崖判定閾値）の読み込み。

第2章「量子化の微調整（スレッショルドの検討）」に対応し、
西上州（岩峰）・多摩（段丘）・横須賀（谷戸）など、地形の性質に応じた
推奨ウィンドウサイズ／閾値を config/regions.json から取得する。
"""

from __future__ import annotations

import json
import os

DEFAULT_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "regions.json"
)


def load_regions(config_path: str = DEFAULT_CONFIG_PATH) -> dict:
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def get_region(name: str, config_path: str = DEFAULT_CONFIG_PATH) -> dict:
    regions = load_regions(config_path)
    if name not in regions:
        available = ", ".join(regions.keys())
        raise KeyError(f"未定義の地域プリセットです: {name}（定義済み: {available}）")
    return regions[name]
