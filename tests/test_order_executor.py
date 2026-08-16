import pandas as pd
from strategy.execution.order_executor import (
    OrderExecutor, Order, can_execute, apply_slippage, calc_liquidity_tier
)
from strategy.adapters.a_share import AShareAdapter


def test_liquidity_tier_dynamic():
    """漏洞 AI：动态流动性判定"""
    assert calc_liquidity_tier(2e8) == "高"
    assert calc_liquidity_tier(7e7) == "中"
    assert calc_liquidity_tier(3e7) == "低"


def test_apply_slippage_dynamic():
    """漏洞 AI：根据成交额动态滑点"""
    price = apply_slippage(100.0, "买入", 2e8)
    assert price == 100.0 * 1.0002   # 高流动性低滑点

    price_low = apply_slippage(100.0, "买入", 3e7)
    assert price_low == 100.0 * 1.001  # 低流动性高滑点


def test_can_execute_t1_veto():
    """漏洞 AE：T+1 当日买入无法卖出"""
    adapter = AShareAdapter()
    assert not adapter.can_sell("2026-08-15", "2026-08-15")
    assert adapter.can_sell("2026-08-14", "2026-08-15")


def test_execute_first_batch_uses_entry_price():
    """漏洞 AJ：首笔订单用 card.entry_price"""
    from strategy.signals.expectation_card import build_expectation_card

    card = build_expectation_card(
        symbol="600519", scene="趋势市",
        entry_price=100, stop_loss=95,
        confidence=0.85,
    )

    executor = OrderExecutor(adapter=AShareAdapter())
    position_size = {"amount": 50000, "pct": 0.05, "entry_strategy": "一次性"}

    # 成交额 7e7 → 中流动性档 → 滑点 0.0005
    current_bar = {"close": 102, "成交额": 7e7, "date": "2026-08-15", "停牌": False}

    orders = executor.execute_first_batch(card, position_size, current_bar)
    assert len(orders) == 1
    assert orders[0].price == 100.0 * 1.0005   # entry_price + slippage


def test_execute_first_batch_volume_correct():
    """漏洞修复：首笔订单量正确（amount 已是最终金额，不再 × pct）"""
    from strategy.signals.expectation_card import build_expectation_card

    card = build_expectation_card(
        symbol="600519", scene="趋势市",
        entry_price=100, stop_loss=95, confidence=0.85,
    )
    executor = OrderExecutor(adapter=AShareAdapter())
    position_size = {"amount": 50000, "pct": 0.05, "entry_strategy": "一次性"}
    current_bar = {"close": 102, "成交额": 7e7, "date": "2026-08-15", "停牌": False}

    orders = executor.execute_first_batch(card, position_size, current_bar)
    assert len(orders) == 1
    # amount 50000 / filled_price 100.05 / 100 = 4.99 → int = 4 → *100 = 400 股
    assert orders[0].volume == 400


def test_can_execute_t1_in_normal_market():
    """漏洞修复：T+1 在正常行情（非涨跌停）也生效"""
    # 正常行情（非涨跌停）
    bar = {"close": 100, "prev_close": 100, "board": "主板"}
    position = {"可卖": False}   # T+1 锁定
    result = can_execute("卖出", bar, position, "2026-08-15")
    assert result == "拒绝（T+1 限制）"

    # 可卖
    position_ok = {"可卖": True}
    result_ok = can_execute("卖出", bar, position_ok, "2026-08-15")
    assert result_ok == "可执行"
