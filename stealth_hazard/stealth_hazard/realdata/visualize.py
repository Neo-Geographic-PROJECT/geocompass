"""解析結果の3パネル可視化（標高／平均斜度／ステルスハザード指数）。

heatmap_export.py のPPM出力は依存パッケージなしの簡易確認用だが、
実データでの検証・卒論への掲載には matplotlib によるカラー可視化が要る。
本モジュールは matplotlib にのみ依存し（numpy/scipy/pyprojの結果を
受け取って描画するだけなので）、DemGridと analyze_np() の出力
（WindowResultのリスト）があれば足りる。

例:
    python3 -m stealth_hazard.realdata.visualize \\
        --dem-csv out/dem_5m.csv --results-csv out/window_50m.csv \\
        --span 10 --title "西上州（window=50m）" --out out/detail.png
"""
from __future__ import annotations

import argparse
import csv

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.family"] = "Yu Gothic"  # 日本語ラベル表示用（Windows既定フォント）


def _load_results_csv(path: str):
    with open(path, encoding="utf-8") as f:
        return [{k: float(v) for k, v in row.items()} for row in csv.DictReader(f)]


def _to_grid(results: list, field: str, span: int) -> np.ndarray:
    nrows = int(max(r["row0"] for r in results) // span) + 1
    ncols = int(max(r["col0"] for r in results) // span) + 1
    grid = np.full((nrows, ncols), np.nan)
    for r in results:
        grid[int(r["row0"] // span), int(r["col0"] // span)] = r[field]
    return grid


def plot_detail(elev: np.ndarray, results: list, span: int, title: str, out_path: str) -> None:
    """標高・平均斜度・ステルスハザード指数の3パネル図を保存する。"""
    slope_grid = _to_grid(results, "mean_slope_deg", span)
    index_grid = _to_grid(results, "index", span)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5.2))
    fig.suptitle(title, fontsize=14)

    im0 = axes[0].imshow(elev, cmap="terrain")
    axes[0].set_title("標高 [m]")
    plt.colorbar(im0, ax=axes[0], fraction=0.046, pad=0.04)

    im1 = axes[1].imshow(slope_grid, cmap="viridis")
    axes[1].set_title("平均斜度 [deg]（マイメッシュ）")
    plt.colorbar(im1, ax=axes[1], fraction=0.046, pad=0.04)

    vmax = np.nanpercentile(index_grid, 99)
    im2 = axes[2].imshow(index_grid, cmap="inferno", vmax=vmax if vmax > 0 else None)
    axes[2].set_title("ステルスハザード指数（崖延長÷平均斜度）")
    plt.colorbar(im2, ax=axes[2], fraction=0.046, pad=0.04)

    for ax in axes:
        ax.set_xticks([])
        ax.set_yticks([])

    plt.tight_layout()
    plt.savefig(out_path, dpi=140)
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="解析結果の3パネル可視化")
    parser.add_argument("--dem-csv", required=True, help="等方DEM格子のCSV（DemGrid.from_csv形式）")
    parser.add_argument("--results-csv", required=True, help="heatmap_export.export_csv()の出力")
    parser.add_argument("--span", type=int, required=True, help="windowed_analysis.cells_per_window()の戻り値")
    parser.add_argument("--title", default="", help="図のタイトル")
    parser.add_argument("--out", required=True, help="出力PNGパス")
    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    elev = np.loadtxt(args.dem_csv, delimiter=",")
    results = _load_results_csv(args.results_csv)
    plot_detail(elev, results, args.span, args.title, args.out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
