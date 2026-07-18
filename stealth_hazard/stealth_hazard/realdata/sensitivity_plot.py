"""複数地域の sensitivity.py 出力CSVを重ねて比較プロットする。

例:
    python3 -m stealth_hazard.realdata.sensitivity_plot \\
        --input 横須賀=out/sensitivity_横須賀.csv --input 多摩=out/sensitivity_多摩.csv \\
        --input 西上州=out/sensitivity_西上州.csv --out out/sensitivity_comparison.png
"""
from __future__ import annotations

import argparse
import csv

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams["font.family"] = "Yu Gothic"  # 日本語ラベル表示用（Windows既定フォント）


def _load_summary_csv(path: str):
    with open(path, encoding="utf-8") as f:
        return [{k: float(v) for k, v in row.items()} for row in csv.DictReader(f)]


def plot_comparison(labeled_csv_paths: dict, out_path: str) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for label, path in labeled_csv_paths.items():
        rows = sorted(_load_summary_csv(path), key=lambda r: r["window_m"])
        windows = [r["window_m"] for r in rows]
        axes[0].plot(windows, [r["p99_index"] for r in rows], marker="o", label=label)
        axes[1].plot(windows, [r["frac_nonzero"] for r in rows], marker="o", label=label)

    axes[0].set_xlabel("window size [m]")
    axes[0].set_ylabel("index 99th percentile")
    axes[0].set_title("ウィンドウサイズ vs 指数(上位1%点)")
    axes[0].set_xscale("log")
    axes[0].legend()

    axes[1].set_xlabel("window size [m]")
    axes[1].set_ylabel("index>0のウィンドウ割合")
    axes[1].set_title("ウィンドウサイズ vs 崖を含むウィンドウの割合")
    axes[1].set_xscale("log")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(out_path, dpi=140)
    plt.close(fig)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="地域間の感度分析比較プロット")
    parser.add_argument(
        "--input", action="append", required=True,
        help="'ラベル=CSVパス' の形式で複数指定可能（例: --input 横須賀=out/a.csv）",
    )
    parser.add_argument("--out", required=True, help="出力PNGパス")
    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    labeled = dict(item.split("=", 1) for item in args.input)
    plot_comparison(labeled, args.out)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
