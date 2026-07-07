"""実DEM（基盤地図情報DEM5A、JPGIS/GML形式）を取り込むための追加モジュール群。

パッケージ本体（dem_grid.py/slope.py/cliff.py/windowed_analysis.py等）は
標準ライブラリのみで完結する参照実装だが、本サブパッケージは実データでの
座標変換・大規模グリッド処理のために numpy / scipy / pyproj を必要とする
（requirements-realdata.txt 参照）。DemGrid/WindowResult のデータ構造は
本体と共通のものをそのまま使う。
"""
