"""解析パイプラインのユニットテスト。

主眼は「平均斜度だけでは見えないハザードを、本指数が検出できること」
という研究仮説そのものを、合成地形を用いて数値的に検証することにある。
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import synthetic_terrain as st  # noqa: E402

from stealth_hazard.cliff import cliff_edges  # noqa: E402
from stealth_hazard.windowed_analysis import analyze  # noqa: E402


class TestFlatTerrain(unittest.TestCase):
    def test_flat_terrain_has_zero_index(self):
        dem = st.flat(rows=10, cols=10)
        results = analyze(dem, window_m=50)
        self.assertTrue(all(r.index == 0.0 for r in results))
        self.assertTrue(all(r.cliff_length_m == 0.0 for r in results))


class TestUniformSlope(unittest.TestCase):
    def test_uniform_gentle_slope_has_no_cliffs(self):
        # rise_per_cell=0.5m, resolution=5m -> 傾き比0.1、閾値(比2.0)を大きく下回る
        dem = st.uniform_slope(rows=10, cols=10, rise_per_cell=0.5)
        self.assertEqual(cliff_edges(dem), [])
        results = analyze(dem, window_m=50)
        self.assertTrue(all(r.index == 0.0 for r in results))
        # 斜度自体はゼロではない（=単なる勾配は検出されているが、崖ではない）
        self.assertTrue(all(r.mean_slope_deg > 0.0 for r in results))


class TestHiddenCliffVsUniformSlope(unittest.TestCase):
    """研究仮説の核心: 「平均斜度が同水準」でも、崖の有無で指数が全く異なることを示す。"""

    def setUp(self):
        self.rows = self.cols = 20
        self.resolution = 5.0

    def test_stealth_hazard_is_detected_despite_gentle_average_slope(self):
        uniform = st.uniform_slope(
            self.rows, self.cols, resolution_m=self.resolution, rise_per_cell=0.5
        )
        hidden = st.hidden_cliff(
            self.rows, self.cols, resolution_m=self.resolution, drop_m=11.0
        )

        uniform_results = analyze(uniform, window_m=100)  # 全体を1ウィンドウに収める
        hidden_results = analyze(hidden, window_m=100)

        self.assertEqual(len(uniform_results), 1)
        self.assertEqual(len(hidden_results), 1)
        uniform_r = uniform_results[0]
        hidden_r = hidden_results[0]

        # 両者とも「一見なだらか」と言える程度の平均斜度に収まっている
        self.assertLess(uniform_r.mean_slope_deg, 10.0)
        self.assertLess(hidden_r.mean_slope_deg, 10.0)

        # 単なる勾配（uniform）は崖を含まないため指数0
        self.assertEqual(uniform_r.index, 0.0)

        # 隠れた崖を含む地形は、平均斜度は同程度でも指数が明確に正になる
        self.assertGreater(hidden_r.cliff_length_m, 0.0)
        self.assertGreater(hidden_r.index, 0.0)
        self.assertGreater(hidden_r.index, uniform_r.index)

    def test_cliff_length_matches_expected_geometry(self):
        # 1本の崖ライン（境界の全列）が検出される -> 崖延長 = cols * resolution
        hidden = st.hidden_cliff(self.rows, self.cols, resolution_m=self.resolution, drop_m=11.0)
        edges = cliff_edges(hidden)
        total_length = sum(length for (_r0, _c0, _r1, _c1, length) in edges)
        self.assertAlmostEqual(total_length, self.cols * self.resolution)


class TestWindowSizeSensitivity(unittest.TestCase):
    """第2章「量子化の微調整」検証: ウィンドウサイズ違いで解像度が変わることを確認する。"""

    def test_smaller_window_localizes_the_hazard(self):
        rows = cols = 40
        resolution = 5.0
        # 上半分だけに隠れた崖を配置し、下半分は完全平坦にする
        dem = st.hidden_cliff(rows, cols, resolution_m=resolution, drop_m=11.0, cliff_row=10)
        for r in range(20, rows):
            for c in range(cols):
                dem.elevations[r][c] = dem.elevations[19][c]

        coarse = analyze(dem, window_m=200)  # 全体を1ウィンドウに集約
        fine = analyze(dem, window_m=50)  # 複数ウィンドウに分割

        self.assertEqual(len(coarse), 1)
        self.assertGreater(len(fine), 1)

        # 細かいウィンドウでは、崖を含まないウィンドウの指数が明確に0になり、
        # 危険箇所が空間的に特定できる（粗いウィンドウでは全域が1つの値に均される）
        zero_index_windows = [r for r in fine if r.index == 0.0]
        nonzero_index_windows = [r for r in fine if r.index > 0.0]
        self.assertTrue(zero_index_windows)
        self.assertTrue(nonzero_index_windows)


if __name__ == "__main__":
    unittest.main()
