import pandas as pd
import numpy as np
from strategy.indicators.traditional import calc_c_traditional

def test_c_traditional_zhongyintai_disabled():
    """中阴态：C_传统 = 0"""
    close = pd.Series([10.0] * 60)
    high = close * 1.01
    low = close * 0.99
    volume = pd.Series([1000.0] * 60)

    result = calc_c_traditional(close, high, low, volume, scene="中阴态")
    assert result["C_传统"] == 0.0

def test_c_traditional_trending_strong():
    """趋势市：均线多头排列 → 高分"""
    close = pd.Series(np.linspace(10, 30, 60))
    high = close * 1.02
    low = close * 0.98
    volume = pd.Series(np.linspace(1000, 2000, 60))

    result = calc_c_traditional(close, high, low, volume, scene="趋势市")
    assert 0.5 < result["C_传统"] <= 1.0

def test_rsi_score_in_uptrend_above_60():
    """漏洞 P：趋势市 RSI ≥ 60 给高分"""
    close = pd.Series(np.linspace(10, 20, 60))  # 持续上涨
    high = close * 1.01
    low = close * 0.99
    volume = pd.Series([1000] * 60)

    result = calc_c_traditional(close, high, low, volume, scene="趋势市")
    assert result["RSI_评分"] >= 0.7

def test_volume_score_guandian_low_volume_bonus():
    """漏洞修复：拐点市 + 低量 → 量价评分 ≥ 0.9
    触发条件：current_vol < volume.tail(20).mean() * 0.5
    构造：最后 20 根中前 19 根高量(1000) + 最后 1 根地量(100)
    → tail(20).mean() = 955, current_vol = 100, 100 < 477.5 ✓
    """
    close = pd.Series(np.linspace(10, 15, 60))
    high = close * 1.01
    low = close * 0.99
    volume = pd.Series([1000.0] * 40 + [1000.0] * 19 + [100.0])
    result = calc_c_traditional(close, high, low, volume, scene="拐点市")
    assert result["量价_评分"] >= 0.9