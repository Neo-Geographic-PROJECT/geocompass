# GeoCompass

地理院タイルを用いた2地点の都市規模比較ツール。メルカトル図法による縮尺の歪みを動的に補正し、離れた2都市を重ねて視覚的に比較できます。

🔗 **公開ページ**: https://neo-geographic-project.github.io/geocompass/

## 主な機能

- 地理院ジオコーダによる地点A・B検索（座標・標高取得）
- オーバーレイ表示（半透明重畳）／左右分割表示の切替
- メルカトル歪み係数のリアルタイム表示・自動補正
- Bのドラッグによる手動オフセット調整
- 視覚化モード（標準／モノクロ／ハイコントラスト／陰影起伏）・道路強調
- 5枠プリセット＋HOME保存（localStorage）
- 現在の比較状態をPNG画像として出力
- 日本語 / English 切替対応

## 技術構成

- Leaflet.js（CDN）
- 地理院タイル（std/pale/blank/photo/hillshademap）
- 地理院ジオコーダ API・標高API
- html2canvas（PNG出力）
- 単体HTMLファイル（`map_compare_v1.1.html`）。外部ビルド不要

## ローカルで動かす

```
npx serve .
```

`http://localhost:<port>/` にアクセスすると `index.html` が `map_compare_v1.1.html` にリダイレクトします。

## 地図の出典について

本ツールは[国土地理院タイル](https://maps.gsi.go.jp/development/ichiran.html)を使用しています。各地図画面右下に「地理院タイル」のクレジットを常時表示しています。

## ライセンス

TBD
