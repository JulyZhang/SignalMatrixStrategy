"""期货适配器（做空预留，ENABLE_SHORT=False 时不启用）"""
import pandas as pd
from strategy.adapters.base import MarketAdapter


class FuturesAdapter(MarketAdapter):
    def get_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        # 期货数据接入（待实现）
        return pd.DataFrame()

    def calc_trading_cost(self, symbol: str, action: str,
                          price: float, volume: int) -> float:
        # 各品种手续费不同，待实现
        return 0.0

    def can_short(self, symbol: str) -> bool:
        return True

    def settlement_rule(self) -> str:
        return "T+0"
