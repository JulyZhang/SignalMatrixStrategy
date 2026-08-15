def test_config_has_atr_period():
    from strategy.config import Config
    assert Config.ATR_PERIOD == 14

def test_config_has_weight_matrix():
    from strategy.config import Config
    assert "趋势市" in Config.WEIGHT_MATRIX
    assert Config.WEIGHT_MATRIX["趋势市"] == {"缠论": 0.5, "SMC": 0.2, "传统": 0.3}

def test_config_has_confidence_tiers():
    from strategy.config import Config
    assert Config.CONFIDENCE_TIERS == {
        "极高": 0.8,
        "高": 0.6,
        "中": 0.5,
        "低": 0.4,
    }

def test_chanlun_soft_caps_uses_condition_keys():
    from strategy.config import Config
    assert set(Config.CHANLUN_SOFT_CAPS.keys()) == {"粘合度", "MACD<0", "成交量"}

def test_chanlun_buypoints_per_regime():
    from strategy.config import Config
    assert Config.CHANLUN_BUYPOINTS["趋势市"]["ban"] == ["一买"]
    assert "类三买" in Config.CHANLUN_BUYPOINTS["拐点市"]["allow"]
