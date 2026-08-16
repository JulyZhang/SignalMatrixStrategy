"""回测脚本：在已有 backtest_data 上跑策略"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
from strategy.data.loader import load_stock_csv
from strategy.main import run_strategy_on_bar


def load_universe_data(symbol: str, data_dir: str = "backtest_data") -> pd.DataFrame:
    """加载单只股票数据"""
    csv_path = os.path.join(data_dir, f"stk_{symbol}.csv")
    return load_stock_csv(csv_path)


def main(symbols: list = None, max_bars: int = None):
    """回测主函数
    max_bars: 单只股票最大回测天数（None = 全跑）
    """
    if symbols is None:
        # 默认用沪深300成分股（用户已有数据）
        data_dir = "backtest_data"
        files = [f.replace("stk_", "").replace(".csv", "")
                 for f in os.listdir(data_dir) if f.startswith("stk_")]
        symbols = files[:5]   # 默认取 5 只测试（10 只全跑超过 10 分钟）

    all_trades = []

    for symbol in symbols:
        df = load_universe_data(symbol)
        if df is None or len(df) < 120:
            continue

        # 限制回测窗口（仅取末尾 max_bars 个交易日）
        end_idx = len(df) if max_bars is None else min(len(df), 120 + max_bars)

        # 逐日回测
        for i in range(120, end_idx):
            daily_close = df["close"].iloc[:i]
            daily_high = df["high"].iloc[:i]
            daily_low = df["low"].iloc[:i]
            daily_volume = df["volume"].iloc[:i]

            # daily_open: 优先用真实开盘价，否则用前一日收盘价近似
            if "open" in df.columns:
                daily_open = df["open"].iloc[:i]
            else:
                daily_open = df["close"].iloc[:i].shift(1).fillna(df["close"].iloc[0])

            weekly_close = daily_close.resample("W").last().dropna()
            weekly_volume = daily_volume.resample("W").sum().dropna()

            current_bar = {
                "close": df["close"].iloc[i],
                "high": df["high"].iloc[i],
                "low": df["low"].iloc[i],
                "成交额": df["close"].iloc[i] * df["volume"].iloc[i],
                "date": str(df.index[i].date()),
                "prev_close": df["close"].iloc[i-1],
                "停牌": False,
            }

            card = run_strategy_on_bar(
                symbol=symbol,
                daily_close=daily_close,
                daily_high=daily_high,
                daily_low=daily_low,
                daily_open=daily_open,
                daily_volume=daily_volume,
                weekly_close=weekly_close,
                weekly_volume=weekly_volume,
                current_bar=current_bar,
            )

            if card:
                all_trades.append({
                    "symbol": symbol,
                    "date": current_bar["date"],
                    "card": card,
                })

    print(f"\n回测完成，共生成 {len(all_trades)} 个有效信号")
    return all_trades


if __name__ == "__main__":
    main()