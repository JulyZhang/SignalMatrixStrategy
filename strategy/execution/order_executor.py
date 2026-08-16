"""订单执行器（衔接第 8 节仓位与第 10 节回测）

修正：
- 漏洞 AD：执行层入口
- 漏洞 AE：T+1 + 涨跌停联动
- 漏洞 AJ：分批不同时序（首笔用 card.entry_price，后续用市价）
- 漏洞 AI：滑点动态判断流动性
"""
from dataclasses import dataclass
from typing import List, Optional

from strategy.config import Config


@dataclass
class Order:
    symbol: str
    action: str
    price: float
    volume: int
    order_type: str = "限价"
    status: str = "待成交"
    created_at: Optional[str] = None
    filled_at: Optional[str] = None
    filled_price: Optional[float] = None


def calc_liquidity_tier(bar_成交额: float) -> str:
    """漏洞 AI：动态流动性判定（三档不重叠）"""
    if bar_成交额 >= 1e8:
        return "高"
    elif bar_成交额 >= 5e7:
        return "中"
    return "低"


def apply_slippage(price: float, action: str, bar_成交额: float) -> float:
    """滑点（根据流动性动态）"""
    tier = calc_liquidity_tier(bar_成交额)
    rate = Config.SLIPPAGE_BY_LIQUIDITY[tier]
    if action == "买入":
        return price * (1 + rate)
    return price * (1 - rate)


def can_execute(action: str, bar: dict, position: dict, current_date: str) -> str:
    """判断订单是否可执行（含涨跌停 + T+1 + 停牌）"""
    prev_close = bar.get("prev_close", bar["close"])
    board = bar.get("board", "主板")

    # 停牌（最先检查）
    if bar.get("停牌"):
        return "无法成交（停牌）"

    # 涨跌停检查
    if bar["close"] >= prev_close * (1 + Config.LIMIT_PCT[board]):
        if action == "买入":
            return "无法成交（涨停无法买入）"
        # 卖出遇涨停：T+1 仍生效
        if position and not position.get("可卖", True):
            return "拒绝（T+1 限制）"
        return "排队"

    if bar["close"] <= prev_close * (1 - Config.LIMIT_PCT[board]):
        if action == "卖出":
            return "无法成交（跌停无法卖出）"
        return "排队"

    # T+1 检查（漏洞 AE — 移到涨跌停之外，正常行情也生效）
    if action == "卖出" and position and not position.get("可卖", True):
        return "拒绝（T+1 限制）"

    return "可执行"


class OrderExecutor:
    def __init__(self, adapter):
        self.adapter = adapter

    def execute_first_batch(self, card, position_size: dict, current_bar: dict) -> List[Order]:
        """首笔订单：用 card.entry_price + 滑点"""
        entry_price = card.entry_price
        filled_price = apply_slippage(entry_price, "买入", current_bar["成交额"])
        # amount 已是仓位金额（含 pct），不再 × pct（修复 plan doubling bug）
        volume = int(position_size["amount"] / filled_price / 100) * 100

        status = can_execute("买入", current_bar, None, current_bar["date"])
        if status == "可执行":
            return [Order(card.symbol, "买入", filled_price, volume, "限价")]
        elif status.startswith("排队"):
            order = Order(card.symbol, "买入", filled_price, volume, "限价")
            order.status = "排队"
            return [order]
        return []

    def execute_additional_batch(self, card, position_size: dict, current_bar: dict,
                                 batch_ratio: float) -> List[Order]:
        """后续批次：用触发时的市价（非 card.entry_price，漏洞 AJ）"""
        # 加仓触发检查
        R = card.entry_price - card.stop_loss
        if R <= 0:
            return []
        current_profit_R = (current_bar["close"] - card.entry_price) / R
        tp1_level = (card.tp1 - card.entry_price) / R
        if current_profit_R < tp1_level:
            return []

        # 使用当前市价
        current_price = current_bar["close"]
        filled_price = apply_slippage(current_price, "买入", current_bar["成交额"])
        volume = int(position_size["amount"] * batch_ratio / filled_price / 100) * 100

        status = can_execute("买入", current_bar, None, current_bar["date"])
        if status == "可执行":
            return [Order(card.symbol, "买入", filled_price, volume, "限价")]
        return []
