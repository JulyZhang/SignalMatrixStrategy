import pandas as pd
import numpy as np
from strategy.indicators.smc import (
    detect_mss_bullish,
    detect_ob_bullish,
    detect_fvg_bullish,
    calc_c_smc,
)

def test_detect_mss_double_confirmation():
    """漏洞 L：双重验证（连续 2 根 或 突破 ≥ 0.5ATR）"""
    # 构造连续 2 根突破
    closes = pd.Series([10, 11, 12, 13, 12.5, 13.5, 14.5, 15.5])
    highs = closes + 0.5
    atr_30 = 1.0

    mss = detect_mss_bullish(closes, highs, atr_30=atr_30, lookback=5)
    assert mss is True

def test_detect_mss_insufficient_move():
    """单根突破幅度不足 → False"""
    closes = pd.Series([10, 10.1, 10.2])   # 涨幅太小
    highs = closes + 0.5
    mss = detect_mss_bullish(closes, highs, atr_30=1.0, lookback=5)
    assert mss is False

def test_detect_ob_bullish_with_unfilled():
    """OB 识别（用收盘价判定，未填充）"""
    # 构造 OB 场景
    ohlc = pd.DataFrame({
        "open": [10, 9, 9, 11, 12],
        "high": [11, 10, 9.5, 11.5, 12.5],
        "low": [9, 8.5, 8.8, 10.5, 11.5],
        "close": [10.5, 8.8, 9.2, 11.2, 12.2],
    })
    ob = detect_ob_bullish(ohlc, mss_occurred=True)
    assert ob is not None
    assert ob["评分"] > 0

def test_calc_c_smc_scene_weighted():
    """C_SMC 场景自适应（震荡市主驱动）"""
    ohlc = pd.DataFrame({
        "open": [10] * 30, "high": [11] * 30,
        "low": [9] * 30, "close": np.linspace(10, 12, 30),
    })
    result = calc_c_smc(ohlc, scene="震荡市", mss_occurred=True)
    assert 0 <= result["C_SMC"] <= 1
    assert "期望空间上沿" in result or result["C_SMC"] == 0