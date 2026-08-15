import pandas as pd
import numpy as np
from strategy.utils.indicators import calc_ema, calc_macd, calc_rsi, calc_macd_hist_mean_abs

def test_calc_ema():
    s = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], dtype=float)
    ema = calc_ema(s, period=5)
    assert len(ema) == 10
    assert abs(ema.iloc[-1] - 8.0) < 0.1

def test_calc_macd():
    """MACD 包含：MACD_line, signal_line, hist"""
    s = pd.Series(np.arange(1, 100, dtype=float))
    macd_line, signal_line, hist = calc_macd(s)
    assert len(macd_line) == 99
    assert len(signal_line) == 99
    assert len(hist) == 99

def test_calc_rsi():
    s = pd.Series(np.arange(1, 30, dtype=float))
    rsi = calc_rsi(s, period=14)
    assert len(rsi) == 29
    # 上涨趋势 RSI 应 > 50
    assert rsi.iloc[-1] > 50

def test_calc_macd_hist_mean_abs_with_epsilon():
    """漏洞 E 除零保护：分母必须包含 ε 保护"""
    from strategy.utils.indicators import calc_macd_hist_mean_abs

    # MACD_hist 全为 0（理论极端情况）
    hist = pd.Series([0.0] * 20)
    mean_abs = calc_macd_hist_mean_abs(hist, window=20)
    assert mean_abs >= 0.0001   # ε 保护生效

def test_calc_macd_hist_mean_abs_normal():
    hist = pd.Series([1.0, -2.0, 3.0, -4.0] * 5)
    mean_abs = calc_macd_hist_mean_abs(hist, window=20)
    assert abs(mean_abs - 2.5) < 0.01