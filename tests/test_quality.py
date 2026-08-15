import pandas as pd
from strategy.data.quality import (
    check_missing_data,
    check_price_outliers,
    is_st_or_suspended,
)


def test_check_missing_data_clean():
    df = pd.DataFrame({"close": [10] * 30}, index=pd.date_range("2024-01-01", periods=30))
    missing = check_missing_data(df)
    assert missing == []


def test_check_missing_data_with_gap():
    dates = pd.date_range("2024-01-01", periods=30)
    df = pd.DataFrame({"close": [10] * 30}, index=dates)
    df = df.drop(df.index[10:15])   # 移除 5 天
    missing = check_missing_data(df, expected_dates=dates)
    assert len(missing) == 5


def test_check_price_outliers():
    # 20 个连续价格 + 1 个显著异常值，确保 median-MAD > 0
    prices = pd.Series(list(range(100, 120)) + [10000.0])
    outliers = check_price_outliers(prices, threshold=5.0)
    assert len(outliers) == 1