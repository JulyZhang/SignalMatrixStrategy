from strategy.signals.expectation_card import build_expectation_card
from strategy.position.sizing import calc_position_size

def test_position_size_5_tiers():
    card = build_expectation_card(
        symbol="X", scene="趋势市",
        entry_price=100, stop_loss=95,
        confidence=0.85,
    )
    result = calc_position_size(card, total_capital=1_000_000, atr_history=[1.0]*50)
    assert result["pct"] == 0.10   # 极高
    assert result["entry_strategy"] == "一次性"

def test_position_size_atr_protection():
    """漏洞 Z：ATR_ratio 数据不足保护"""
    card = build_expectation_card(
        symbol="X", scene="趋势市",
        entry_price=100, stop_loss=95,
        confidence=0.85,
    )
    # 数据不足
    result = calc_position_size(card, total_capital=1_000_000, atr_history=[1.0]*30)
    # 应不缩放
    assert result["pct"] == 0.10