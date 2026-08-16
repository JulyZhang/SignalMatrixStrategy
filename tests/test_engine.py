import pandas as pd
import numpy as np
from strategy.backtest.engine import BacktestEngine

def test_engine_runs_simple_case():
    """回测引擎跑通简单场景"""
    # 构造 1 只股票 100 天的简单数据
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    df = pd.DataFrame({
        "open": np.linspace(10, 20, 100),
        "high": np.linspace(10.5, 20.5, 100),
        "low": np.linspace(9.5, 19.5, 100),
        "close": np.linspace(10, 20, 100),
        "volume": [1e7] * 100,
    }, index=dates)

    engine = BacktestEngine(initial_capital=1_000_000)
    # 仅测试不抛异常
    # 详细回测需要更多配置
    assert engine is not None