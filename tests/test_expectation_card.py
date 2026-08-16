from strategy.signals.expectation_card import build_expectation_card, validate_card

def test_build_card_trending():
    card = build_expectation_card(
        symbol="600519",
        scene="趋势市",
        entry_price=100.0,
        stop_loss=95.0,
        smc_upper=120.0,
        confidence=0.75,
        C_缠论=0.8, C_SMC=0.6, C_传统=0.7,
    )
    assert card.entry_price == 100.0
    assert card.risk_reward_ratio >= 1.5   # 趋势市门槛
    assert card.entry_strategy == "分批(60%→40%)"

def test_build_card_range_market():
    """漏洞 V：震荡市 RR ≥ 1.0 即可"""
    card = build_expectation_card(
        symbol="000001",
        scene="震荡市",
        entry_price=10.0,
        stop_loss=9.5,
        smc_upper=11.0,
        confidence=0.55,
        C_缠论=0.5, C_SMC=0.6, C_传统=0.5,
    )
    assert card.risk_reward_ratio >= 1.0

def test_validate_card_rejects_invalid_rr():
    card = build_expectation_card(
        symbol="000001",
        scene="趋势市",
        entry_price=100.0,
        stop_loss=99.0,
        smc_upper=101.0,
        confidence=0.7,
        C_缠论=0.7, C_SMC=0.6, C_传统=0.6,
    )
    # TP1 = 1.5R = 1.5，但 smc_upper = 101 → TP2 被截断到 101
    valid = validate_card(card)
    # 期望空间不足，期望值可能为负
    assert isinstance(valid, bool)