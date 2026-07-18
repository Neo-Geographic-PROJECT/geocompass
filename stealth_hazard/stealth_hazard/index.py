"""独自指標「地形難易度指数」の定義。

    index = 崖延長の合算（複雑性） ÷ 平均斜度（基底勾配）

単なる平均斜度だけでは埋もれてしまう、局所的な崖の集中度（ラフネス）を
浮き上がらせるための指標。平均斜度が低いにもかかわらず本指数が高い
マイメッシュは、道路等の人工物にカモフラージュされた
「ステルスハザード」の候補地点となる。
"""

EPSILON = 1e-6


def difficulty_index(cliff_length_m: float, mean_slope_deg: float) -> float:
    """平均斜度が実質ゼロ（完全な平地）の場合は0を返す。"""
    if mean_slope_deg <= EPSILON:
        return 0.0
    return cliff_length_m / mean_slope_deg
