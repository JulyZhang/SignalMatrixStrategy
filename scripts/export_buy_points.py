"""导出买点检测结果到 CSV，便于人工核对准确性

用法：
    python scripts/export_buy_points.py --symbols 000875,600546,601636,300145,002493
    python scripts/export_buy_points.py --symbols 000875 --step 1   # 每天检测（更密集）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
from pathlib import Path

import pandas as pd

from strategy.data.loader import load_stock_csv
from strategy.indicators.chanlun import detect_buy_point, detect_zhongshu


def export_one(symbol: str, data_dir: str = "backtest_data",
               output_dir: str = "./results",
               lookback: int = 120,
               step: int = 5) -> int:
    """导出单只股票的买点检测结果

    Args:
        step: 每 N 天检测一次（默认 5 = 周级别；1 = 日级别密集扫描）

    Returns:
        检测到的买点数
    """
    csv_path = os.path.join(data_dir, f"stk_{symbol}.csv")
    if not os.path.exists(csv_path):
        print(f"  缺失数据: {csv_path}")
        return 0

    df = load_stock_csv(csv_path)
    if df is None or len(df) == 0:
        print(f"  加载失败: {csv_path}")
        return 0

    high = df['high']
    low = df['low']
    close = df['close']
    volume = df['volume'] if 'volume' in df.columns else None

    rows = []
    state = {'last_one_buy_idx': -1, 'last_one_buy_low': float('inf')}
    zhongshus = None   # 懒加载

    # 滑动窗口检测
    for i in range(lookback, len(df), step):
        h = high.iloc[:i+1]
        l = low.iloc[:i+1]
        c = close.iloc[:i+1]
        v = volume.iloc[:i+1] if volume is not None else None

        # 懒加载中枢（每 N 步刷新一次，避免重复计算）
        if zhongshus is None or i % (lookback * 2) == lookback:
            zhongshus = detect_zhongshu(h, l)

        bp, state = detect_buy_point(h, l, c, volumes=v, zhongshus=zhongshus, state=state)

        if bp is not None:
            # 收集买点 + 周边上下文（前后 5 天）
            date = df.index[i].date()
            ctx_start = max(0, i - 5)
            ctx_end = min(len(df), i + 6)
            ctx = df.iloc[ctx_start:ctx_end]

            row = {
                'symbol': symbol,
                'date': str(date),
                'buy_type': bp.type,
                'price': bp.price,
                'confidence': bp.confidence,
                'reason': bp.reason,
                # 周边 5 日高低点（用于核对）
                'pre5_high': ctx['high'].iloc[0] if len(ctx) > 0 else None,
                'pre5_low': ctx['low'].iloc[0] if len(ctx) > 0 else None,
                'pre5_close': ctx['close'].iloc[0] if len(ctx) > 0 else None,
                'current_high': df['high'].iloc[i],
                'current_low': df['low'].iloc[i],
                'current_close': df['close'].iloc[i],
                'post5_high': ctx['high'].iloc[-1] if len(ctx) > 0 else None,
                'post5_low': ctx['low'].iloc[-1] if len(ctx) > 0 else None,
                'post5_close': ctx['close'].iloc[-1] if len(ctx) > 0 else None,
                # 当前 MACD_hist（用于核对底背离/金叉）
                'macd_hist': None,   # 占位
                'volume': df['volume'].iloc[i] if 'volume' in df.columns else None,
                'vol_vs_ma5': None,   # 占位
                'zhongshus_count': len(zhongshus) if zhongshus else 0,
            }

            # 计算 MACD_hist 和 vol_vs_ma5
            from strategy.utils.indicators import calc_macd
            _, _, hist = calc_macd(close.iloc[:i+1])
            row['macd_hist'] = round(hist.iloc[-1], 4)

            if volume is not None and i >= 5:
                ma5_vol = volume.iloc[i-5:i].mean()
                if ma5_vol > 0:
                    row['vol_vs_ma5'] = round(volume.iloc[i] / ma5_vol, 2)

            # 附加信息（如一买低点、二买的一买 idx）
            if bp.extra:
                for k, val in bp.extra.items():
                    row[f'extra_{k}'] = val

            rows.append(row)

    if not rows:
        print(f"  {symbol}: 0 个买点")
        return 0

    out = pd.DataFrame(rows)

    # 输出文件名
    os.makedirs(output_dir, exist_ok=True)
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(output_dir, f"buy_points_{symbol}_{timestamp}.csv")
    out.to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"  {symbol}: {len(rows)} 个买点 -> {out_path}")
    print(f"    一买: {(out['buy_type'] == '一买').sum()}, "
          f"二买: {(out['buy_type'] == '二买').sum()}, "
          f"三买: {(out['buy_type'] == '三买').sum()}")

    return len(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", type=str, required=True,
                        help="逗号分隔的 6 位股票代码")
    parser.add_argument("--step", type=int, default=5,
                        help="检测步长（默认 5 = 周级别；1 = 日级别密集）")
    parser.add_argument("--lookback", type=int, default=120,
                        help="回看窗口（默认 120 根 K 线）")
    parser.add_argument("--data-dir", type=str, default="backtest_data")
    parser.add_argument("--output-dir", type=str, default="./results")
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]

    total = 0
    for sym in symbols:
        total += export_one(sym, args.data_dir, args.output_dir, args.lookback, args.step)

    print(f"\n总计: {total} 个买点导出到 {args.output_dir}/")


if __name__ == "__main__":
    main()
