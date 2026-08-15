"""数据加载：CSV 文件 + akshare 接口（回测/实盘共用）"""
import pandas as pd
import os
import warnings


def load_stock_csv(csv_path: str) -> pd.DataFrame | None:
    """加载单只股票 CSV（backtest_data/stk_XXXXXX.csv 格式）

    返回：OHLCV DataFrame，index 为 DatetimeIndex
    """
    if not os.path.exists(csv_path):
        return None
    try:
        df = pd.read_csv(csv_path)
        # 标准化列名（中英文）
        col_map = {"日期": "date", "开盘": "open", "最高": "high",
                   "最低": "low", "收盘": "close", "成交量": "volume"}
        df = df.rename(columns=col_map)

        # 定位日期列
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.set_index("date").sort_index()
        elif isinstance(df.index, pd.DatetimeIndex):
            df = df.sort_index()
        else:
            return None

        # 必需列校验
        required = {"open", "high", "low", "close", "volume"}
        if not required.issubset(df.columns):
            return None
        return df
    except Exception as e:
        warnings.warn(f"加载 {csv_path} 失败: {e}")
        return None


def load_index_csv(csv_path: str) -> pd.DataFrame | None:
    """加载指数 CSV（如 csi300.csv, csi_div.csv）"""
    return load_stock_csv(csv_path)
