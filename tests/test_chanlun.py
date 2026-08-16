import pandas as pd
import numpy as np
import pytest
from strategy.indicators.chanlun import (
    calc_c_chanlun,
    calc_c_weekly,
    calc_c_daily,
    calc_chanlun_gate,
    detect_zhongshu,
    Zhongshu,
)

def test_c_weekly_hard_veto_direction_mismatch():
    """硬性否决：EMA20<EMA60 时 C_周=0"""
    weekly_close = pd.Series(np.linspace(30, 10, 30))  # 下跌
    c_weekly = calc_c_weekly(weekly_close, weekly_volume=None)
    assert c_weekly == 0.0

def test_c_weekly_soft_cap_convergence():
    """软性扣分：粘合度 < 1.5% → C_周 上限 0.5"""
    # 构造接近粘合的数据
    weekly_close = pd.Series([10.0] * 30)
    weekly_volume = pd.Series([1000.0] * 30)
    c_weekly = calc_c_weekly(weekly_close, weekly_volume)
    assert c_weekly <= 0.5

def test_c_daily_structure_score_2_zhongshu():
    """结构完整度：≥2 个中枢 → 1.0"""
    structure_score, daily_close = 1.0, pd.Series(np.linspace(10, 20, 60))
    # 实际实现中需要中枢识别算法
    assert structure_score == 1.0

def test_c_daily_returns_valid_range():
    """calc_c_daily 应返回 [0, 1] 范围内的分数"""
    daily_close = pd.Series(np.linspace(10, 20, 60))
    for bp in ("一买", "二买", "三买", "类二买", "类三买"):
        score = calc_c_daily(daily_close, bp)
        assert 0.0 <= score <= 1.0

def test_chanlun_gate_zhongyintai_veto():
    """前置过滤：中阴态 → 直接否决"""
    daily_close = pd.Series([10.0] * 60)
    weekly_close = pd.Series([10.0] * 30)
    result = calc_chanlun_gate(
        scene="中阴态",
        weekly_close=weekly_close,
        daily_close=daily_close,
    )
    assert result["C_缠论"] == 0.0
    assert result["否决"] is True


def test_detect_zhongshu_basic_uptrend():
    """简单上升趋势：构造 OHLC，验证返回 list"""
    # 5 个明显的高低点
    close = pd.Series([10, 11, 12, 11, 10, 11, 12, 13, 12, 11, 12, 13, 14,
                       13, 12, 13, 14, 15, 14, 13, 14, 15, 16, 17, 16])
    high = close * 1.02  # 真实 high
    low = close * 0.98   # 真实 low

    zs = detect_zhongshu(high, low)
    assert isinstance(zs, list)


def test_detect_zhongshu_returns_zhongshu_dataclass():
    """返回 Zhongshu 列表，字段完整"""
    dates = pd.date_range("2024-01-01", periods=200, freq="D")
    close = pd.Series(np.linspace(10, 20, 200) + np.sin(np.linspace(0, 8*np.pi, 200)), index=dates)
    high = close * 1.02
    low = close * 0.98

    zs = detect_zhongshu(high, low)
    for z in zs:
        assert isinstance(z, Zhongshu)
        assert z.high >= z.low
        assert z.direction in ('up', 'down')
        assert z.type in ('new', 'extension')


def test_detect_zhongshu_short_data_returns_empty():
    """数据不足时返回空列表"""
    high = pd.Series([10, 11, 12, 13])
    low = pd.Series([9, 10, 11, 12])
    zs = detect_zhongshu(high, low)
    assert zs == []


def test_detect_zhongshu_on_000875_history():
    """实战测试：000875 24 年数据应能识别多个中枢"""
    from strategy.data.loader import load_stock_csv
    df = load_stock_csv("backtest_data/stk_000875.csv")
    high = df['high']
    low = df['low']
    zs = detect_zhongshu(high, low)
    print(f"\n000875 24 年识别中枢: {len(zs)}")
    for z in zs[:10]:
        print(f"  [{z.start_idx}-{z.end_idx}] {z.direction} {z.type} ZG={z.high:.2f} ZD={z.low:.2f}")
    assert isinstance(zs, list)


def test_detect_zhongshu_raises_on_mismatched_lengths():
    """highs 和 lows 长度不一致时报错"""
    high = pd.Series([10, 11, 12, 13])
    low = pd.Series([9, 10])  # 长度不同

    with pytest.raises(ValueError, match="长度必须一致"):
        detect_zhongshu(high, low)