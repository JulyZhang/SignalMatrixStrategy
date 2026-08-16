"""A 股适配器（漏洞 AE T+1 + 涨跌停联动）"""
import pandas as pd
from strategy.adapters.base import MarketAdapter
from strategy.config import Config


class AShareAdapter(MarketAdapter):
    def get_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        from strategy.data.loader import load_stock_csv
        return load_stock_csv(f"backtest_data/stk_{symbol}.csv")

    def calc_trading_cost(self, symbol: str, action: str,
                          price: float, volume: int) -> float:
        成交金额 = price * volume
        佣金 = max(成交金额 * Config.COMMISSION_RATE, 5.0)   # 5 元最低佣金（A 股行业规则）
        过户费 = 成交金额 * Config.TRANSFER_FEE
        if action == "卖出":
            印花税 = 成交金额 * Config.STAMP_TAX_SELL
            return 佣金 + 印花税 + 过户费
        return 佣金 + 过户费

    def can_short(self, symbol: str) -> bool:
        return False

    def settlement_rule(self) -> str:
        return "T+1"

    def is_limit_up(self, current: float, prev_close: float, board: str = "主板") -> bool:
        threshold = prev_close * (1 + Config.LIMIT_PCT[board])
        return current >= threshold

    def is_limit_down(self, current: float, prev_close: float, board: str = "主板") -> bool:
        threshold = prev_close * (1 - Config.LIMIT_PCT[board])
        return current <= threshold

    def can_sell(self, position_buy_date: str, current_date: str) -> bool:
        """T+1 检查（漏洞 AE）"""
        return position_buy_date != current_date
