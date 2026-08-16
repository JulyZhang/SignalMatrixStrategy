"""从本地全 A 日 K zip 包导入全历史数据到 backtest_data/

源数据：D:\\BaiduNetdiskDownload\\股票历史数据(1)\\全A日K\\{year}.zip
       每个 zip 含 YYYY/{code}.{exchange}.csv 文件
       27 列：datetime/open/high/low/close/volume(amount 是万元,volume 是手)

输出：backtest_data/stk_{6位代码}.csv
      兼容 strategy.data.loader.load_stock_csv
      volume 转股（× 100），成交额保留万元（loader 不需要）

用法：
    python scripts/import_full_history.py --symbols 000875,600546
    python scripts/import_full_history.py --symbols 600519 --start 2010
    python scripts/import_full_history.py --symbols 000875,600546 --overwrite
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import argparse
import zipfile
import io
from pathlib import Path

import pandas as pd


SOURCE_DIR = r"D:\BaiduNetdiskDownload\股票历史数据(1)\全A日K"
DATA_DIR = "backtest_data"


def import_one(symbol: str, source_dir: str = SOURCE_DIR,
               data_dir: str = DATA_DIR,
               start_year: int = None,
               overwrite: bool = False) -> bool:
    """导入单只股票的全历史到 backtest_data/stk_{symbol}.csv"""
    csv_path = os.path.join(data_dir, f"stk_{symbol}.csv")

    if os.path.exists(csv_path) and not overwrite:
        print(f"  跳过（已存在）: {csv_path}")
        return True

    all_rows = []
    years_tried = 0
    years_hit = 0

    # 按年份遍历 zip
    for year in range(start_year or 2000, 2027):
        zip_path = os.path.join(source_dir, f"{year}.zip")
        if not os.path.exists(zip_path):
            continue
        years_tried += 1

        # 找到匹配 symbol 的 csv（可能有 .SH 或 .SZ 后缀）
        candidates = [
            f"{year}/{symbol}.SH.csv",
            f"{year}/{symbol}.SZ.csv",
            f"{year}/{symbol}.BJ.csv",
        ]

        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in candidates:
                try:
                    with zf.open(name) as f:
                        df_year = pd.read_csv(f, encoding="utf-8")
                    if not df_year.empty:
                        all_rows.append(df_year)
                        years_hit += 1
                    break   # 找到了就不再试其他后缀
                except KeyError:
                    continue

    if not all_rows:
        print(f"  无数据: {symbol}")
        return False

    # 合并 + 排序
    df = pd.concat(all_rows, ignore_index=True)
    df = df.drop_duplicates(subset="datetime", keep="last").sort_values("datetime").reset_index(drop=True)

    # 转换为目标格式（兼容 strategy.data.loader）
    out = pd.DataFrame({
        "日期": pd.to_datetime(df["datetime"]).dt.strftime("%Y-%m-%d"),
        "股票代码": symbol,
        "开盘": df["open"].values,
        "收盘": df["close"].values,
        "最高": df["high"].values,
        "最低": df["low"].values,
        # volume 是手 → 转为股（× 100）
        "成交量": (df["volume"].astype(float) * 100).round(0).values,
        # amount 已是万元
        "成交额": df["amount"].astype(float).round(0).values,
        # 振幅 = (high - low) / prev_close * 100
        "振幅": ((df["high"].astype(float) - df["low"].astype(float)) / df["pre_close"].astype(float) * 100).round(2).values,
        # 涨跌幅（源数据有 pct_chg）
        "涨跌幅": df["pct_chg"].astype(float).round(2).values,
        # 涨跌额（源数据有 change）
        "涨跌额": df["change"].astype(float).round(2).values,
        # 换手率
        "换手率": df["turnover"].astype(float).round(2).values,
    })

    os.makedirs(data_dir, exist_ok=True)
    out.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"  保存: {csv_path}")
    print(f"    {years_hit}/{years_tried} 年份命中, {len(out)} 行, {df['datetime'].iloc[0]} ~ {df['datetime'].iloc[-1]}")
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", type=str, required=True,
                        help="逗号分隔的 6 位股票代码（如 '000875,600546'）")
    parser.add_argument("--start", type=int, default=2000,
                        help="起始年份（默认 2000）")
    parser.add_argument("--overwrite", action="store_true",
                        help="覆盖已有文件")
    parser.add_argument("--source-dir", type=str, default=SOURCE_DIR,
                        help=f"源 zip 目录（默认 {SOURCE_DIR}）")
    parser.add_argument("--data-dir", type=str, default=DATA_DIR,
                        help="输出目录")
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    if not os.path.exists(args.source_dir):
        print(f"源目录不存在: {args.source_dir}")
        return

    success, fail = 0, 0
    for i, sym in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] {sym}")
        if import_one(sym, args.source_dir, args.data_dir, args.start, args.overwrite):
            success += 1
        else:
            fail += 1

    print(f"\n完成: {success} 成功, {fail} 失败")


if __name__ == "__main__":
    main()