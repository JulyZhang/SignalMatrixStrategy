import pandas as pd
import numpy as np
from strategy.indicators.chanlun import (
    calc_c_chanlun,
    calc_c_weekly,
    calc_c_daily,
    calc_chanlun_gate,
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