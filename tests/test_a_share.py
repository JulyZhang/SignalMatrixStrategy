from strategy.adapters.a_share import AShareAdapter

def test_a_share_t1():
    adapter = AShareAdapter()
    assert adapter.settlement_rule() == "T+1"
    assert adapter.can_short("600519") is False

def test_a_share_trading_cost():
    adapter = AShareAdapter()
    # 买入 100 股 @ 100 元
    cost_buy = adapter.calc_trading_cost("600519", "买入", 100.0, 100)
    # commission = max(3.0, 5.0) = 5.0; transfer = 0.10
    assert abs(cost_buy - 5.10) < 0.001   # 5 元最低佣金 + 过户费

    # 卖出 100 股 @ 110 元
    cost_sell = adapter.calc_trading_cost("600519", "卖出", 110.0, 100)
    # commission = max(3.3, 5.0) = 5.0; stamp = 11.0; transfer = 0.11
    assert abs(cost_sell - 16.11) < 0.001
    assert cost_sell > cost_buy   # 卖出有印花税

def test_a_share_limit_check():
    adapter = AShareAdapter()
    prev_close = 100.0
    # 主板涨停 110
    assert adapter.is_limit_up(prev_close * 1.10, prev_close, board="主板")
    # 跌停
    assert adapter.is_limit_down(prev_close * 0.90, prev_close, board="主板")
