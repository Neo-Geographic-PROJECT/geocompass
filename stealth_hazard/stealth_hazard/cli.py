"""CLIエントリポイント。

例:
    python3 -m stealth_hazard.cli --dem examples/data/sample.csv \\
        --resolution 5 --windows 50,20,10 --out-dir out/

    python3 -m stealth_hazard.cli --dem examples/data/sample.csv \\
        --resolution 5 --region 横須賀 --out-dir out/

複数のウィンドウサイズを指定すると、各サイズでの指数分布を比較し、
どのスケールで「ステルスハザード」が最も顕在化するかを検証できる。
"""

from __future__ import annotations

import argparse
import os
import statistics

from .dem_grid import DemGrid
from .heatmap_export import export_csv, export_heatmap_ppm
from .regions import get_region
from .windowed_analysis import analyze, cells_per_window


def _summarize(results: list, window_m: float) -> None:
    indices = [r.index for r in results]
    slopes = [r.mean_slope_deg for r in results]
    print(
        f"[window={window_m}m] n={len(indices)} "
        f"mean_index={statistics.mean(indices):.2f} "
        f"max_index={max(indices):.2f} "
        f"mean_slope={statistics.mean(slopes):.2f}deg"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ステルスハザード指数解析ツール")
    parser.add_argument("--dem", required=True, help="DEM CSVファイルパス（カンマ区切り標高グリッド）")
    parser.add_argument("--resolution", type=float, default=5.0, help="DEMのセル間隔[m]（既定: 5mメッシュ）")
    parser.add_argument("--windows", default="50,20,10", help="比較するウィンドウサイズ[m]（カンマ区切り）")
    parser.add_argument("--region", default=None, help="config/regions.json の地域プリセット名（--windowsより優先）")
    parser.add_argument("--out-dir", default="out", help="出力ディレクトリ")
    parser.add_argument(
        "--cliff-threshold-deg",
        type=float,
        default=None,
        help="崖判定の斜度閾値[度]（既定: 約63.4度 = 水平5mで比高10m以上に相当）",
    )
    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)

    dem = DemGrid.from_csv(args.dem, args.resolution)
    os.makedirs(args.out_dir, exist_ok=True)

    windows = [float(w) for w in args.windows.split(",")]
    cliff_threshold_deg = args.cliff_threshold_deg

    if args.region is not None:
        preset = get_region(args.region)
        windows = [float(preset["window_m"])]
        if cliff_threshold_deg is None:
            cliff_threshold_deg = float(preset["cliff_threshold_deg"])
        print(f"[region={args.region}] {preset.get('note', '')}")

    kwargs = {}
    if cliff_threshold_deg is not None:
        kwargs["cliff_slope_threshold_deg"] = cliff_threshold_deg

    for window_m in windows:
        results = analyze(dem, window_m, **kwargs)
        _summarize(results, window_m)
        span = cells_per_window(dem, window_m)
        base = f"window_{int(window_m)}m"
        export_csv(results, os.path.join(args.out_dir, base + ".csv"))
        export_heatmap_ppm(results, span, os.path.join(args.out_dir, base + ".ppm"))


if __name__ == "__main__":
    main()
