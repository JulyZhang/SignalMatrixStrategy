"""仓位追踪（漏洞 AK 按批次追踪 + FIFO 卖出）

A 股 T+1 规则：
- buy_date < current_date → 可卖 = True
- buy_date == current_date → 仍锁定
- 每日盘后调用 next_day_unlock(current_date) 解锁符合条件批次
"""
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class PositionLot:
    price: float
    volume: int
    buy_date: str
    可卖: bool = False

    def unlock(self, current_date: str):
        """A 股 T+1：买入次日即可卖"""
        if self.buy_date < current_date:
            self.可卖 = True


class PositionTracker:
    def __init__(self):
        self.lots: Dict[str, List[PositionLot]] = {}

    def update(self, symbol: str, fill_price: float, fill_volume: int, current_date: str):
        new_lot = PositionLot(fill_price, fill_volume, current_date)
        if symbol not in self.lots:
            self.lots[symbol] = []
        self.lots[symbol].append(new_lot)

    def next_day_unlock(self, current_date: str):
        """批量解锁可卖批次（A 股 T+1：buy_date < current_date 即次日可卖）"""
        for lots in self.lots.values():
            for lot in lots:
                lot.unlock(current_date)

    def get_sellable_volume(self, symbol: str) -> int:
        if symbol not in self.lots:
            return 0
        return sum(lot.volume for lot in self.lots[symbol] if lot.可卖)

    def sell_fifo(self, symbol: str, volume: int) -> float:
        if symbol not in self.lots:
            return 0.0
        remaining = volume
        总成本 = 0.0
        for lot in self.lots[symbol]:
            if not lot.可卖 or remaining <= 0:
                continue
            卖出量 = min(lot.volume, remaining)
            总成本 += lot.price * 卖出量
            lot.volume -= 卖出量
            remaining -= 卖出量
        self.lots[symbol] = [lot for lot in self.lots[symbol] if lot.volume > 0]
        return 总成本