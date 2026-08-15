import pandas as pd
import numpy as np
from strategy.utils.atr import calc_atr, calc_atr_mean

def test_calc_atr_basic():
    """测试 ATR(14) 计算（漏洞 I：零值保护）"""
    high = pd.Series([10, 11, 12, 13, 14] * 5, dtype=float)
    low = pd.Series([9, 10, 11, 12, 13] * 5, dtype=float)
    close = pd.Series([9.5, 10.5, 11.5, 12.5, 13.5] * 5, dtype=float)

    atr = calc_atr(high, low, close, period=14)
    assert len(atr) == 25
    assert atr.iloc[-1] > 0
    assert not atr.isna().all()

def test_calc_atr_zero_volatility():
    """漏洞 I：零值保护（停牌或极端低波动）"""
    high = pd.Series([10.0] * 20)
    low = pd.Series([10.0] * 20)
    close = pd.Series([10.0] * 20)

    atr = calc_atr(high, low, close, period=14)
    assert atr.iloc[-1] == 0.0   # 零波动返回 0，不抛异常

def test_calc_atr_mean():
    """测试均值计算（含数据不足保护）"""
    from strategy.utils.atr import calc_atr_mean

    atr_series = pd.Series([1.0] * 30)
    mean = calc_atr_mean(atr_series, window=50)
    assert mean == 1.0   # 不足时返回序列均值

    atr_series_50 = pd.Series([2.0] * 50)
    mean = calc_atr_mean(atr_series_50, window=50)
    assert mean == 2.0
