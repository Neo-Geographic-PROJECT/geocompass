"""realdata.fast_windowed_analysis.analyze_np() の回帰テスト。

numpy/scipy/pyproj が無い環境では実データ変換パイプライン自体を使わないため、
本テストは numpy が見つからない場合はスキップする。
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import synthetic_terrain as st  # noqa: E402

from stealth_hazard.windowed_analysis import analyze  # noqa: E402

try:
    import numpy  # noqa: F401

    from stealth_hazard.realdata.fast_windowed_analysis import analyze_np

    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


@unittest.skipUnless(NUMPY_AVAILABLE, "numpyが導入されていないためスキップ")
class TestAnalyzeNpMatchesReference(unittest.TestCase):
    """実データの大規模グリッド用に書き直したanalyze_np()が、合成地形での
    参照実装(windowed_analysis.analyze)と数値的に一致することを確認する。
    実データそのものでの検証は D:\\scratch\\dem_work で別途実施済み。
    """

    def _assert_matches(self, dem, window_m):
        expected = analyze(dem, window_m)
        actual = analyze_np(dem, window_m)
        self.assertEqual(len(expected), len(actual))
        for e, a in zip(expected, actual):
            self.assertEqual((e.row0, e.col0, e.row1, e.col1), (a.row0, a.col0, a.row1, a.col1))
            for field in ("max_elev", "min_elev", "relief", "mean_slope_deg", "cliff_length_m", "index"):
                self.assertAlmostEqual(getattr(e, field), getattr(a, field), places=9)

    def test_flat_terrain(self):
        self._assert_matches(st.flat(rows=12, cols=15), window_m=20)

    def test_uniform_slope(self):
        self._assert_matches(st.uniform_slope(rows=12, cols=15), window_m=20)

    def test_hidden_cliff(self):
        self._assert_matches(st.hidden_cliff(rows=20, cols=20, drop_m=11.0), window_m=25)

    def test_rocky_peak_with_ragged_window(self):
        # rows/colsがwindowの倍数にならない場合(端が欠けたウィンドウ)も一致するか確認
        self._assert_matches(st.rocky_peak(rows=23, cols=17), window_m=30)


if __name__ == "__main__":
    unittest.main()
