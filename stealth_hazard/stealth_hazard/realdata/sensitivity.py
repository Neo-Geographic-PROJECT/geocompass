"""ウィンドウサイズ感度分析（第2章「量子化の微調整」の実験パート）。

「どのスケールでステルスハザードが最も顕在化するか」を横並びで検証するため、
複数のウィンドウサイズで analyze_np() を実行し、指数の分布がどう変化するかを
CSVに書き出す。

注意: 指数・カバー率は一般にウィンドウサイズに対して単調増加する
（崖延長はウィンドウ面積とともに素直に積算されるのに対し、平均斜度は
それほど伸びないため）。これは集計上の効果であり、「大きいウィンドウほど
危険」ではなく「大きいウィンドウほど崖を拾いやすい」だけであることに注意。
異なる地域・ウィンドウサイズ間で指数の絶対値を単純比較しないこと。

例:
    python3 -m stealth_hazard.realdata.sensitivity \\
        --gml-glob "path/to/tiles/*.xml" --windows 5,10,15,20,30,50,75,100,150,200 \\
        --out-csv out/sensitivity_西上州.csv
"""
from __future__ import annotations

import argparse
import time

import numpy as np

from ..cliff import DEFAULT_CLIFF_SLOPE_DEG
from ..dem_grid import DemGrid
from ..regions import get_region
from .build_grid import build_dem_grid_from_gml
from .fast_windowed_analysis import analyze_np


def run_sensitivity(dem: DemGrid, windows: list, cliff_slope_threshold_deg: float = DEFAULT_CLIFF_SLOPE_DEG) -> list:
    """各ウィンドウサイズでanalyze_np()を実行し、指数分布の要約統計を返す。"""
    rows = []
    for window_m in windows:
        t0 = time.time()
        results = analyze_np(dem, window_m, cliff_slope_threshold_deg=cliff_slope_threshold_deg)
        indices = np.array([r.index for r in results])
        rows.append(
            {
                "window_m": window_m,
                "n_windows": len(results),
                "mean_index": float(indices.mean()),
                "p99_index": float(np.percentile(indices, 99)),
                "max_index": float(indices.max()),
                "frac_nonzero": float((indices > 0).mean()),
                "elapsed_s": time.time() - t0,
            }
        )
    return rows


def write_summary_csv(rows: list, path: str) -> None:
    import csv

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ウィンドウサイズ感度分析")
    parser.add_argument("--gml-glob", required=True, help="GMLタイルのglobパターン")
    parser.add_argument("--windows", default="5,10,15,20,30,50,75,100,150,200", help="比較するウィンドウサイズ[m]（カンマ区切り）")
    parser.add_argument("--region", default=None, help="config/regions.json の地域プリセット名（崖判定閾値の取得用）")
    parser.add_argument("--out-csv", required=True, help="要約統計CSVの出力パス")
    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    windows = [float(w) for w in args.windows.split(",")]
    threshold = DEFAULT_CLIFF_SLOPE_DEG
    if args.region is not None:
        threshold = float(get_region(args.region)["cliff_threshold_deg"])

    dem = build_dem_grid_from_gml(args.gml_glob)
    rows = run_sensitivity(dem, windows, cliff_slope_threshold_deg=threshold)
    for r in rows:
        print(
            f"window={r['window_m']}m n={r['n_windows']} max={r['max_index']:.2f} "
            f"p99={r['p99_index']:.2f} frac_nonzero={r['frac_nonzero']:.3f} ({r['elapsed_s']:.1f}s)"
        )
    write_summary_csv(rows, args.out_csv)
    print(f"wrote {args.out_csv}")


if __name__ == "__main__":
    main()
