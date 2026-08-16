import pandas as pd
import numpy as np
from strategy.scoring.scene import recognize_scene

def _make_weekly_ma_convergence():
    """均线粘合（触发中阴态）"""
    dates = pd.date_range("2024-01-01", periods=60, freq="W")
    close = pd.Series([10.0] * 60, index=dates)   # 几乎无变化
    return close

def _make_strong_uptrend():
    dates = pd.date_range("2024-01-01", periods=60, freq="D")
    close = pd.Series(np.linspace(10, 30, 60), index=dates)
    return close

def test_scene_zhongyintai_via_convergence():
    close = _make_weekly_ma_convergence()
    scene = recognize_scene(close)
    assert scene == "中阴态"

def test_scene_trending_up():
    close = _make_strong_uptrend()
    scene = recognize_scene(close)
    assert scene in ("趋势市", "拐点市")   # 强趋势

def test_scene_returns_one_of_four():
    close = _make_strong_uptrend()
    scene = recognize_scene(close)
    assert scene in ("趋势市", "震荡市", "拐点市", "中阴态")

def test_scene_short_series_defaults_zhongyintai():
    """数据不足时兜底为中阴态（宁可错过原则）"""
    # 仅有 20 个点，低于所有 helper 的最小数据要求
    dates = pd.date_range("2024-01-01", periods=20, freq="D")
    close = pd.Series(np.linspace(10, 11, 20), index=dates)
    scene = recognize_scene(close)
    # 兜底应为中阴态
    assert scene == "中阴态"

def test_scene_random_returns_one_of_four():
    """随机数据应落入 4 个场景之一（不抛错）"""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=60, freq="D")
    close = pd.Series(np.random.normal(10, 0.5, 60), index=dates)
    scene = recognize_scene(close)
    assert scene in ("趋势市", "震荡市", "拐点市", "中阴态")