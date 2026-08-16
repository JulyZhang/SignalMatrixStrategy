from strategy.scoring.weighted import calc_weighted_score

def test_weighted_zhongyintai_veto():
    """漏洞 R：中阴态防御性否决"""
    result = calc_weighted_score(
        scene="中阴态",
        C_缠论=0.8, C_SMC=0.7, C_传统=0.5,
    )
    assert result["C_总"] == 0.0
    assert result["否决"] is True

def test_weighted_trend_market():
    """趋势市权重：缠论 50% + SMC 20% + 传统 30%"""
    result = calc_weighted_score(
        scene="趋势市",
        C_缠论=0.8, C_SMC=0.5, C_传统=0.7,
    )
    expected = 0.5 * 0.8 + 0.2 * 0.5 + 0.3 * 0.7
    assert abs(result["C_总"] - expected) < 0.01

def test_weighted_extreme_chanlun_veto():
    """漏洞 S：非拐点市 C_缠论 < 0.3 否决"""
    result = calc_weighted_score(
        scene="趋势市",
        C_缠论=0.2, C_SMC=0.7, C_传统=0.5,
    )
    assert result["C_总"] == 0.0

def test_weighted_confidence_tier():
    """置信度档位映射"""
    result = calc_weighted_score(
        scene="趋势市",
        C_缠论=0.85, C_SMC=0.8, C_传统=0.8,
    )
    assert result["置信度档位"] == "极高"
