import os
from scripts.run_backtest import load_universe_data
from scripts.calc_metrics import calc_metrics

def test_load_universe_data():
    df = load_universe_data("600519", data_dir="backtest_data")
    if df is not None:
        assert "close" in df.columns
        assert len(df) > 0


def test_calc_metrics_empty():
    """空 trades：返回 0/0/0.0 + 空分布字典"""
    metrics = calc_metrics([])
    assert metrics["total_signals"] == 0
    assert metrics["symbols_count"] == 0
    assert metrics["avg_confidence"] == 0.0
    assert metrics["scene_distribution"] == {}
    assert metrics["confidence_tier_distribution"] == {}


def test_calc_metrics_one_trade():
    """单笔 trade：分布字典含 1 个键、统计正确"""
    from strategy.signals.expectation_card import build_expectation_card
    card = build_expectation_card(
        symbol="600519", scene="趋势市",
        entry_price=100, stop_loss=95, confidence=0.85,
    )
    trades = [{"symbol": "600519", "date": "2026-08-15", "card": card}]
    metrics = calc_metrics(trades)
    assert metrics["total_signals"] == 1
    assert metrics["symbols_count"] == 1
    assert metrics["avg_confidence"] == 0.85
    assert metrics["scene_distribution"] == {"趋势市": 1}
    assert metrics["confidence_tier_distribution"][card.confidence_tier] == 1