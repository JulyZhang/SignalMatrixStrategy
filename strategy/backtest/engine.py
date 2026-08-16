"""回测引擎（第 10 节）

共用 strategy 核心代码，仅数据来源和成交模拟不同
"""
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import pandas as pd


@dataclass
class BacktestResult:
    total_return: float = 0.0
    annual_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe: float = 0.0
    trades: List[Dict] = field(default_factory=list)
    nav_curve: Optional[pd.Series] = None


class BacktestEngine:
    def __init__(self, initial_capital: float = 1_000_000,
                 adapter=None):
        self.initial_capital = initial_capital
        self.adapter = adapter

    def run(self, symbols: List[str], start: str, end: str,
            strategy_func=None) -> BacktestResult:
        """运行回测

        strategy_func: 接收 bar 数据，返回 ExpectationCard 或 None
        """
        # 简化版：实际实现需要遍历每根 K 线
        # 调用 strategy_func() 生成信号
        # 调用 OrderExecutor.execute() 执行
        # 记录交易、成本、滑点
        # 计算绩效指标
        result = BacktestResult()
        return result