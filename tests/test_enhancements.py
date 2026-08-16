"""增强功能测试（增强 1/2/3）

覆盖：
- 增强 1：历史阻力位降权（×0.7）
- 增强 2：乖离率约束（封顶"高"档）
- 增强 3：MSS 5根时效检测 + 一买不限 MSS
"""
import pytest
import pandas as pd
import numpy as np

from strategy.scoring.weighted import calc_weighted_score
from strategy.indicators.smc import detect_mss_within_window


def test_resistance_penalty_high_position():
    """历史阻力位降权：当前价 ≥ 85% 1年高点 → C_总 ×0.7"""
    dates = pd.date_range("2024-01-01", periods=300, freq="D")
    # 价格从 10 涨到 18（最后一段接近 18.0）
    daily_close = pd.Series(np.linspace(10, 18, 300), index=dates)

    # 当前价 = 18.0，1 年高点（rolling 252）= 18.0
    # ratio = 1.0 > 0.85 → 触发 ×0.7 折扣
    result = calc_weighted_score(
        scene="趋势市",
        C_缠论=0.8, C_SMC=0.6, C_传统=0.7,
        current_price=18.0, daily_close=daily_close,
    )
    # 不触发否决，应该有 C_总（但被折扣）
    assert result["否决"] is False
    # C_总 = 0.5*0.8 + 0.2*0.6 + 0.3*0.7 = 0.73
    # 折扣后 = 0.73 * 0.7 = 0.511
    assert 0.40 < result["C_总"] <= 0.55, f"expected discount applied, got {result['C_总']}"


def test_resistance_penalty_low_position():
    """历史阻力位降权：当前价 < 85% 1年高点 → 不折扣"""
    dates = pd.date_range("2024-01-01", periods=300, freq="D")
    daily_close = pd.Series(np.linspace(10, 20, 300), index=dates)

    # 当前价 = 12，1 年高点 = 20，比值 = 0.6 < 0.85 → 不触发
    result = calc_weighted_score(
        scene="趋势市",
        C_缠论=0.8, C_SMC=0.6, C_传统=0.7,
        current_price=12.0, daily_close=daily_close,
    )
    # C_总 = 0.5*0.8 + 0.2*0.6 + 0.3*0.7 = 0.73（无折扣）
    assert result["C_总"] == pytest.approx(0.73, abs=0.01)


def test_bollinger_30_threshold_caps_confidence():
    """乖离率约束：价格 > EMA120 × 1.30 → C_总封顶 0.79"""
    dates = pd.date_range("2024-01-01", periods=200, freq="D")
    # 价格稳定后跳涨 50%（远超 30%）
    daily_close = pd.Series(
        list(np.linspace(10, 12, 180)) + list(np.linspace(12, 18, 20)),
        index=dates,
    )

    # 当前价 = 18，EMA120 ≈ 11.x，bias = (18-11)/11 ≈ 0.636 > 0.30
    result = calc_weighted_score(
        scene="趋势市",
        C_缠论=0.9, C_SMC=0.8, C_传统=0.85,
        current_price=18.0, daily_close=daily_close,
    )
    # C_总理论值 = 0.5*0.9 + 0.2*0.8 + 0.3*0.85 = 0.815（封顶 0.79）
    assert result["C_总"] <= 0.79, f"expected C_总 ≤ 0.79, got {result['C_总']}"
    # 不应该是"极高"档（≥0.80）
    assert result["置信度档位"] != "极高", f"got tier {result['置信度档位']}"


def test_buy2_mss_5bar_required():
    """二买 MSS 5根时效：MSS 在 5 根内 → True"""
    # 构造最近 5 根 K 线有明显 MSS
    closes = [10, 10.5, 11, 11.5, 12, 13, 14]
    ohlc = pd.DataFrame({
        "open": closes,
        "high": [c + 0.3 for c in closes],
        "low": [c - 0.3 for c in closes],
        "close": closes,
    })

    # atr_30=1.0，prev_high（不含最后一根）= 11.5
    # cond_a: closes[-1]=14 > 11.5 AND closes[-2]=13 > 11.5 → True
    result = detect_mss_within_window(ohlc, atr_30=1.0, buy_point="二买", window=5)
    assert result is True


def test_buy1_mss_not_required():
    """一买 MSS 不限时效：即使没有 MSS → 仍 True"""
    # 即便没有 MSS，一买也通过
    flat_closes = [10] * 7
    ohlc_flat = pd.DataFrame({
        "open": flat_closes,
        "high": [c + 0.3 for c in flat_closes],
        "low": [c - 0.3 for c in flat_closes],
        "close": flat_closes,
    })
    result = detect_mss_within_window(ohlc_flat, atr_30=1.0, buy_point="一买", window=5)
    assert result is True   # 一买不限 MSS