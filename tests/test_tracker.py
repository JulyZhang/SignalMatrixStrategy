from strategy.position.tracker import PositionLot, PositionTracker

def test_position_lot_t1_unlock():
    lot = PositionLot(price=100, volume=1000, buy_date="2026-08-15")
    assert not lot.可卖
    lot.unlock("2026-08-16")
    assert lot.可卖

def test_tracker_fifo_sell():
    tracker = PositionTracker()
    tracker.update("X", 100, 500, "2026-08-10")   # 历史持仓
    tracker.update("X", 110, 500, "2026-08-14")   # 8/14 加仓（8/14 < 8/16 → 可卖）

    tracker.next_day_unlock("2026-08-16")

    sellable = tracker.get_sellable_volume("X")
    assert sellable == 1000  # 两批都可卖

    cost = tracker.sell_fifo("X", 300)
    assert cost == 300 * 100   # FIFO 先卖老批次（100 元）


def test_tracker_t1_boundary_mixed():
    """T+1 边界：同日买入的不同批次不能卖；前日买入的批次可以卖"""
    tracker = PositionTracker()
    tracker.update("X", 100, 500, "2026-08-15")   # 8/15 买
    tracker.update("Y", 100, 500, "2026-08-10")   # 8/10 买

    tracker.next_day_unlock("2026-08-16")

    # 8/15 batch: 8/15 < 8/16 → 可卖（按 A 股真实 T+1）
    assert tracker.get_sellable_volume("X") == 500
    # 8/10 batch: 早就可卖
    assert tracker.get_sellable_volume("Y") == 500

    # 验证同日买入仍锁定
    tracker2 = PositionTracker()
    tracker2.update("Z", 100, 500, "2026-08-16")   # 当日买
    tracker2.next_day_unlock("2026-08-16")          # 当日解锁（无效）
    assert tracker2.get_sellable_volume("Z") == 0   # T+1 锁定