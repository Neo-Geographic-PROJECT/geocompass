"""合成DEMを使ったエンドツーエンド動作確認スクリプト。

実データ（基盤地図情報DEM5A）を用意していない段階でも、
パイプライン全体（DEM生成→解析→エクスポート）が動くことを確認できる。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests"))

import synthetic_terrain as st  # noqa: E402

from stealth_hazard.heatmap_export import export_csv, export_heatmap_ppm  # noqa: E402
from stealth_hazard.windowed_analysis import analyze, cells_per_window  # noqa: E402


def main() -> None:
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    os.makedirs(out_dir, exist_ok=True)

    print("=== 多摩・横須賀を模した「隠れた崖」地形（40x40, 5mメッシュ）===")
    dem = st.hidden_cliff(rows=40, cols=40, resolution_m=5.0, drop_m=11.0, cliff_row=15)

    for window_m in (50, 20, 10):
        results = analyze(dem, window_m=window_m)
        indices = [r.index for r in results]
        slopes = [r.mean_slope_deg for r in results]
        print(
            f"window={window_m:>3}m  n={len(results):>3}  "
            f"mean_index={sum(indices) / len(indices):6.2f}  "
            f"max_index={max(indices):6.2f}  "
            f"mean_slope={sum(slopes) / len(slopes):5.2f}deg"
        )
        span = cells_per_window(dem, window_m)
        base = os.path.join(out_dir, f"demo_window_{window_m}m")
        export_csv(results, base + ".csv")
        export_heatmap_ppm(results, span, base + ".ppm")

    print(f"\nCSV/PPM出力先: {out_dir}")
    print("PPMは image viewer や `convert demo_window_10m.ppm demo.png` (ImageMagick) 等で確認可能")


if __name__ == "__main__":
    main()
