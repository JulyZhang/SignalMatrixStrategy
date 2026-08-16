import pandas as pd
from strategy.universe.selector import filter_universe

def test_filter_universe_excludes_low_price():
    """🟩 额外发现：股价 ≥ 1 元过滤"""
    universe = ["A", "B", "C"]
    prices = {"A": 5.0, "B": 0.5, "C": 100.0}
    avg_turnovers = {"A": 1e8, "B": 1e8, "C": 1e8}
    market_caps = {"A": 1e10, "B": 1e10, "C": 1e10}

    result = filter_universe(universe, prices, avg_turnovers, market_caps)
    assert "B" not in result
    assert "A" in result

def test_filter_universe_excludes_low_turnover():
    """漏洞 AF：20 日均成交额 ≥ 5000 万"""
    universe = ["A", "B"]
    prices = {"A": 10.0, "B": 10.0}
    avg_turnovers = {"A": 1e8, "B": 1e7}   # B 流动性不足
    market_caps = {"A": 1e10, "B": 1e10}

    result = filter_universe(universe, prices, avg_turnovers, market_caps)
    assert "B" not in result

def test_filter_universe_skips_listing_days_when_none():
    """未传 listing_days 时不强制检查（防止回归：之前用 `or {}` 会触发空 dict 检查）"""
    universe = ["A"]
    prices = {"A": 10.0}
    avg_turnovers = {"A": 1e8}
    market_caps = {"A": 1e10}
    result = filter_universe(universe, prices, avg_turnovers, market_caps, listing_days=None)
    assert "A" in result   # 不被 90 天最小上市过滤掉

def test_filter_universe_respects_listing_days_when_provided():
    """显式传 listing_days 时按规则过滤"""
    universe = ["NEW", "OLD"]
    prices = {"NEW": 10.0, "OLD": 10.0}
    avg_turnovers = {"NEW": 1e8, "OLD": 1e8}
    market_caps = {"NEW": 1e10, "OLD": 1e10}
    listing_days = {"NEW": 30, "OLD": 200}
    result = filter_universe(universe, prices, avg_turnovers, market_caps, listing_days=listing_days)
    assert "NEW" not in result   # 30 < 90
    assert "OLD" in result       # 200 ≥ 90