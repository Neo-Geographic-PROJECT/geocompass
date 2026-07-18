# ステルスハザード解析システム — 第2章 システム設計

「シン・卒論」第2章「解析手法の現代的定義（量子化の再設計）」に対応する、
5mメッシュDEMから独自指標「地形難易度指数」を算出するための技術的実装。

第1章で述べた1985年当時の0.2mm規定（アナログな地形図の制約）を、
現代の数値標高モデル（DEM）とPythonによる自動計算で再定義し、
「崖延長の合算（複雑性）÷ 平均斜度（基底勾配）」という指数として
定式化・検証するためのプロトタイプである。

## 1. 目的とスコープ

- 目的: 平均斜度だけでは見えない「荒れ具合（ラフネス）」＝ステルスハザードを、
  5mメッシュDEMのマイメッシュ（窓）解析から自動抽出する。
- スコープ: 本ディレクトリは**アルゴリズムと検証手法そのものの設計**に主眼を置く。
  実データ（基盤地図情報DEM5A）を用いた広域解析・3Dモデリング（第4〜5章）は
  次フェーズで本設計の上に構築する。
- 実行環境の制約: 現在の実行環境には numpy / rasterio が導入されていないため、
  本実装は **Python標準ライブラリのみ**で完結する参照実装（reference implementation）
  とした。アルゴリズムの正しさは合成地形に対するユニットテストで検証済み。
  本番運用（実DEMタイル・広域）への移行パスは §6 に記載する。

## 2. 全体アーキテクチャ

```
DEM入力(CSV/将来GeoTIFF)
        │
        ▼
  DemGrid (dem_grid.py)         ── 標高値の2次元グリッド抽象化
        │
        ├──▶ slope.py           ── セル単位の斜度（度）を計算
        │
        ├──▶ cliff.py           ── 隣接セル間の崖判定・崖エッジ抽出
        │
        ▼
  windowed_analysis.py          ── マイメッシュ（window_m四方）単位に集計
        │   ・最高/最低標高・比高
        │   ・平均斜度
        │   ・崖延長合算
        │   ・difficulty_index() を適用
        ▼
  index.py                      ── 指数定義: 崖延長合算 ÷ 平均斜度
        │
        ▼
  heatmap_export.py             ── CSV（検証用）/ PPM（簡易可視化）出力
                                    → 将来: GeoTIFF/PNGデカール化しUVマッピング(第5章)へ
```

`regions.py` + `config/regions.json` は、西上州／多摩／横須賀など
地域ごとに異なる最適ウィンドウサイズ・閾値をプリセットとして保持する
（第2章「量子化の微調整」に対応）。

## 3. 崖判定基準の定式化

1:25,000地形図で等高線が0.2mm以下に密集する条件を実距離に換算すると、

```
0.2mm × 25,000 = 5,000mm = 5m（水平距離）
```

等高線の主曲線間隔を10mとすると、水平5mで比高10m以上 ⇒

```
tan(θ) = 10m / 5m = 2.0  ⇒  θ = atan(2.0) ≈ 63.43°
```

これを `cliff.py` の `DEFAULT_CLIFF_SLOPE_DEG` として定義し、
5mメッシュの隣接セル間（上下・左右）の高低差から崖エッジを検出する。
検出は「右方向」「下方向」のみを走査することで、同一エッジの二重カウントを防止している。

## 4. 指数の定義

```
index = 崖延長合算[m] ÷ 平均斜度[度]        (平均斜度が実質ゼロの場合は0)
```

- 分子（崖延長合算）: マイメッシュ内で検出された崖エッジの長さの総和。
  局所的な垂直方向の断絶＝「複雑性」を表す。
- 分母（平均斜度）: マイメッシュ全体の平均的な傾き＝「基底勾配」。
  分母が小さい（＝一見なだらか）のに分子が大きい（＝実は崖が集中している）場所ほど、
  指数が跳ね上がる ── これが「道路等にカモフラージュされた真のリスク」を
  炙り出す仕組みである。

`tests/test_pipeline.py` では、
「平均斜度がほぼ同水準の2地形」を合成データで作り、
崖を含まない地形は index=0、崖を1本含む地形は index>0 になることを
数値で確認しており、これが本研究の核心的主張（平均勾配だけでは検出できない）
の最小限の証明になっている。

## 5. マイメッシュサイズと地域プリセット（`config/regions.json`）

第2章の「量子化の微調整（スレッショルドの検討）」に対応する、地域ごとの推奨設定：

| 地域           | window_m | 意図                                             |
|----------------|---------:|--------------------------------------------------|
| 西上州（岩峰）  | 50       | 広域の断絶度を抽出（岩峰そのものが十分に大きい）  |
| 多摩（段丘）    | 15       | 道路ノイズに隠れた微細な崖の連続性を抽出          |
| 横須賀（谷戸）  | 10       | 高解像度ウィンドウで谷戸地形の細い崖を検出        |

`cli.py --region <名前>` でこのプリセットを読み込める。
複数の `--windows 50,20,10` を同時比較することで、
「どのスケールでステルスハザードが最も顕在化するか」を横並びで検証できる。

## 6. 本番運用への移行パス — `stealth_hazard.realdata` で実装済み

現行のPure Python実装（本体パッケージ）は正しさの検証と設計の明確化を優先した
参照実装のままとし、実データでの広域解析は `stealth_hazard/realdata/` サブパッケージ
（`numpy`/`scipy`/`pyproj` が必要、`requirements-realdata.txt` 参照）として追加した。

1. `gml_parser.py` — FG-GML DEM5A/5Bタイル（JPGIS2014 GML形式）を直接パース。
   基盤地図情報ダウンロードデータファイル仕様書5.2版および国土地理院公式FAQ
   （Q.4-2/Q.4-4/Q.4-17, https://www.gsi.go.jp/kiban/faq.html）で確認した
   走査順序・nodata規則に基づく
2. `build_grid.py` — 緯度経度の散布点をJGD2011平面直角座標系へ再投影し、
   **真に等方な5m格子**へ最近傍法でリサンプリング。DEM5Aは実際には
   0.2秒×0.2秒の経緯度格子であり南北約6.2m×東西約5.1m（東京付近）の
   長方形グリッドであるため（GSI公式FAQ Q.4-2）、`cliff.py`の崖判定閾値
   atan(2.0)≈63.4°（隣接セル間隔5m前提）を実データに正しく適用するには
   このリサンプリングが必須。海岸線等で不定形になるカバレッジは、
   調査対象外領域（海・未選択域）を補完せず「実測値のみの最大矩形」を抽出して対処する
3. `fast_windowed_analysis.py` — `windowed_analysis.analyze()` のnumpyベクトル化版。
   本体の総当たりループは実データ規模（数百万〜数千万セル）では計算量的に
   非現実的なため（`cliff_edges`のウィンドウ内再走査がウィンドウ数×エッジ数の
   オーダーになる）作成した。`tests/test_fast_windowed_analysis.py` で
   合成地形を用いて本体の参照実装との数値的完全一致を検証済み
4. `heatmap_export.py` の PPM 出力は変更なし。GeoTIFF・PNGデカール出力
   （第5章の3Dモデル表面へのUVマッピング用テクスチャ）は次のステップ

`DemGrid` / `WindowResult` のデータ構造（インターフェース）は本体・realdata間で
完全に共通のまま実装できており、上位モジュール（CLI・エクスポート）への
影響なく置換できることを実証した。

## 7. 実行方法

```bash
cd stealth_hazard

# 合成DEMでのエンドツーエンド動作確認（推奨: 最初に実行）
python3 examples/demo.py

# ユニットテスト（研究仮説の数値的検証）
python3 -m unittest discover -s tests -v

# 実データ（CSV形式の標高グリッド）がある場合
python3 -m stealth_hazard.cli --dem path/to/dem.csv --resolution 5 \
    --windows 50,20,10 --out-dir out/

# 地域プリセットを使う場合
python3 -m stealth_hazard.cli --dem path/to/dem.csv --resolution 5 \
    --region 横須賀 --out-dir out/

# 実DEM(GML)を直接読み込む場合（numpy/scipy/pyproj/matplotlib が必要）
pip install -r requirements-realdata.txt
python3 -m stealth_hazard.realdata.cli \
    --gml-glob "path/to/FG-GML-*-DEM5A-*.xml" --region 横須賀 \
    --out-dir out/ --save-csv out/dem_5m.csv

# 標高・平均斜度・指数の3パネル可視化
python3 -m stealth_hazard.realdata.visualize \
    --dem-csv out/dem_5m.csv --results-csv out/window_10m.csv --span 2 \
    --title "横須賀（window=10m）" --out out/detail.png

# ウィンドウサイズ感度分析（第2章「量子化の微調整」の実験パート）
python3 -m stealth_hazard.realdata.sensitivity \
    --gml-glob "path/to/FG-GML-*-DEM5A-*.xml" --region 横須賀 \
    --windows 5,10,15,20,30,50,75,100,150,200 --out-csv out/sensitivity_横須賀.csv
python3 -m stealth_hazard.realdata.sensitivity_plot \
    --input 横須賀=out/sensitivity_横須賀.csv --out out/sensitivity_comparison.png
```

基盤地図情報ダウンロードサービス（要利用者登録, https://service.gsi.go.jp/kiban/app/）
からDEM5Aタイル(JPGIS/GML形式)をダウンロードし、`--gml-glob`にzipを展開したxml群を
指定する。ダウンロードデータは測量法上の基本測量成果であり、卒論内での利用・引用は
「論文利用」として申請不要だが、解析結果（ヒートマップ・3Dモデル等）を不特定多数が
閲覧可能な場所（公開Webサイト等）で公表する場合は測量法第30条の使用承認が別途必要
になりうる（https://www.gsi.go.jp/LAW/2930-qa.html Q1-4, Q2-3, 事例2-2-3/2-2-4）。
本リポジトリでは実DEM由来の出力物（CSV/PPM/3Dモデル等）はコミットしない運用としている。

## 8. 次のステップ

- ✅ 基盤地図情報からの実DEM5Aタイル取得・解析（`stealth_hazard.realdata`、下仁田・荒船山・
  十石峠を含む西上州エリア／多摩／横須賀の3地域で実データ検証済み。西上州で
  「平均斜度は中央値以下だが崖延長が大きく指数が突出する」候補を複数確認し、
  第2章の核心仮説を実地形上で数値的に裏付けた）
- ✅ ウィンドウサイズ×閾値の感度分析（`realdata.sensitivity`/`sensitivity_plot`）。
  ただし指数・カバー率はウィンドウサイズに対して単調増加する（崖延長がウィンドウ
  面積とともに積算される集計上の効果）ため、地域間・サイズ間で指数の絶対値を
  単純比較しない注意が必要。全サイズを通じて西上州＞横須賀＞多摩の順で指数が高く、
  地形の性質を反映していることは確認済み
- ✅ `numpy` 導入後の実装置換とパフォーマンス比較（`fast_windowed_analysis.py`、
  合成地形で参照実装との数値的完全一致を検証済み）
- `rasterio`/GeoTIFF入出力への対応（現状は緯度経度→平面直角座標系への再投影＋
  最近傍リサンプリングをGMLパーサー内で自前実装）
- 第5章向け: ヒートマップのテクスチャ化とSTL/OBJへのUVマッピングPoC
