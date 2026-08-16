"""市场适配器基类"""
from abc import ABC, abstractmethod
import pandas as pd


class MarketAdapter(ABC):
    @abstractmethod
    def get_data(self, symbol: str, timeframe: str) -> pd.DataFrame: ...

    @abstractmethod
    def calc_trading_cost(self, symbol: str, action: str,
                          price: float, volume: int) -> float: ...

    @abstractmethod
    def can_short(self, symbol: str) -> bool: ...

    @abstractmethod
    def settlement_rule(self) -> str: ...
