import pandas as pd
import os
from strategy.data.loader import load_stock_csv, load_index_csv


def test_load_stock_csv_exists(tmp_path):
    csv_path = tmp_path / "test_600519.csv"
    df = pd.DataFrame({
        "date": pd.date_range("2024-01-01", periods=10),
        "open": range(10), "high": range(10), "low": range(10),
        "close": range(10), "volume": [100] * 10
    })
    df.to_csv(csv_path, index=False)

    result = load_stock_csv(str(csv_path))
    assert len(result) == 10
    assert "close" in result.columns


def test_load_stock_csv_missing_returns_none(tmp_path):
    missing = tmp_path / "nonexistent.csv"
    result = load_stock_csv(str(missing))
    assert result is None


def test_load_stock_csv_real_format(tmp_path):
    """测试真实数据格式：首列无名整数 + 日期在第二列"""
    csv_path = tmp_path / "stk_600519.csv"
    df = pd.DataFrame({
        "日期": pd.date_range("2024-01-01", periods=10),
        "股票代码": ["600519"] * 10,
        "开盘": range(10), "收盘": range(10), "最高": range(10),
        "最低": range(10), "成交量": [100] * 10,
    })
    df.to_csv(csv_path, index=False)  # 注意：index=False，模拟真实格式

    result = load_stock_csv(str(csv_path))
    assert result is not None
    assert isinstance(result.index, pd.DatetimeIndex)  # 关键断言
    assert "close" in result.columns


def test_load_stock_csv_real_file():
    """真实数据 smoke test：加载 backtest_data/stk_600519.csv 验证 DatetimeIndex

    跳过条件：文件不存在（CI 环境可能没有）
    """
    import os
    real = os.path.join("backtest_data", "stk_600519.csv")
    if not os.path.exists(real):
        import pytest
        pytest.skip("real data file not present")
    df = load_stock_csv(real)
    assert df is not None
    assert isinstance(df.index, pd.DatetimeIndex)
    assert {"open", "high", "low", "close", "volume"}.issubset(df.columns)
