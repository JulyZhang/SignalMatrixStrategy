"""数据质量检查（第 11 节数据质量监控）"""
import pandas as pd
import numpy as np


def check_missing_data(df: pd.DataFrame, expected_dates: pd.DatetimeIndex = None) -> list:
    """检查缺失日期"""
    if expected_dates is None:
        return []
    actual_dates = set(df.index)
    missing = [d for d in expected_dates if d not in actual_dates]
    return missing


def check_price_outliers(prices: pd.Series, threshold: float = 5.0) -> list:
    """检查异常价格（超过 N 倍中位数绝对偏差）"""
    median = prices.median()
    mad = (prices - median).abs().median()
    if mad == 0:
        return []
    z_scores = (prices - median).abs() / mad
    return prices.index[z_scores > threshold].tolist()


def is_st_or_suspended(symbol: str, st_list: set, suspended_list: set) -> bool:
    """检查 ST 或停牌状态（实盘时接入公告数据）"""
    return symbol in st_list or symbol in suspended_list