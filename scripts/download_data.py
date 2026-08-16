"""下载 A 股历史数据到 backtest_data/

数据源（三层 fallback，自动降级）：
  1. 通达信（mootdx，TCP 7709，不封 IP）— 主源
  2. 东财 push2his（HTTP，零鉴权）— 一级备胎
  3. 腾讯 web.ifzq.gtimg.cn（HTTP，零鉴权，不封 IP）— 二级备胎
输出格式：与 backtest_data/stk_*.csv 兼容

用法：
    python scripts/download_data.py                    # 下载默认股票列表
    python scripts/download_data.py --symbols 600519,000333  # 指定股票
    python scripts/download_data.py --all               # 下载 backtest_data/ 已有全部股票
    python scripts/download_data.py --skip-mootdx      # 跳过 mootdx 直接走东财
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import argparse
import json
import socket
import urllib.request
from pathlib import Path

import pandas as pd
import requests
from mootdx.quotes import Quotes

# === 从 a-stock-data skill 借鉴的 mootdx helper（带 BESTIP bug 规避）===

_TDX_SERVERS = [
    ('119.97.185.59', 7709), ('124.70.133.119', 7709), ('116.205.183.150', 7709),
    ('123.60.73.44', 7709),  ('116.205.163.254', 7709), ('121.36.225.169', 7709),
    ('123.60.70.228', 7709), ('124.71.9.153', 7709),    ('110.41.147.114', 7709),
    ('124.71.187.122', 7709),
]


def _probe(ip, port, timeout=2.0):
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except Exception:
        return False


def _validate(client, market='std'):
    if market != 'std':
        return True
    try:
        df = client.bars(symbol='000001', frequency=9, offset=1)
        return df is not None and not df.empty
    except Exception:
        return False


def tdx_client(market='std'):
    """建立 mootdx 客户端。

    先扫描已知可用服务器（带 TCP 探活），再回退到 mootdx 内置
    `bestip=True` / 默认两种连接方式。无法连接任何服务端时抛
    RuntimeError。
    """
    for ip, port in _TDX_SERVERS:
        if not _probe(ip, port):
            continue
        try:
            c = Quotes.factory(market=market, server=(ip, port))
            if _validate(c, market):
                return c
        except Exception:
            continue
    for kwargs in ({'bestip': True}, {}):
        try:
            c = Quotes.factory(market=market, **kwargs)
            if _validate(c, market):
                return c
        except Exception:
            continue
    raise RuntimeError("所有 mootdx 服务器均不可用")


# === 东财 HTTP 备胎源（push2his，HTTPS 零鉴权）===

_EASTMONEY_URL = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
_EASTMONEY_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://quote.eastmoney.com/",
}
_EASTMONEY_TIMEOUT = 15


def fetch_kline_eastmoney(symbol: str, days: int = 5000) -> pd.DataFrame | None:
    """从东财 push2his 拉取日 K 线（HTTP，零鉴权，不封 IP）

    Args:
        symbol: 6 位代码（如 '000875'）
        days: 拉取天数（klt=101 日级，lmt=N）

    Returns:
        DataFrame columns: datetime, open, close, high, low, vol
        或 None（失败/空数据）
    """
    # 沪市 secid=1, 深市 secid=0
    secid = "1." + symbol if symbol.startswith(("6", "9")) else "0." + symbol
    params = {
        "secid": secid,
        "ut": "fa5fd1943c7b386f17246893d60d217b",
        "fields1": "f1,f2,f3,f4,f5,f6",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
        "klt": "101",   # 日 K
        "fqt": "1",     # 前复权
        "lmt": str(days),
        "end": "20500101",
    }
    try:
        r = requests.get(_EASTMONEY_URL, params=params,
                         headers=_EASTMONEY_HEADERS, timeout=_EASTMONEY_TIMEOUT)
        data = r.json().get("data", {})
        klines = data.get("klines", [])
        if not klines:
            print(f"    [eastmoney] {symbol} 返空（可能代码错误或停牌）")
            return None
        rows = []
        for line in klines:
            parts = line.split(",")
            # 格式: 日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率
            if len(parts) < 6:
                continue
            rows.append({
                "datetime": parts[0],
                "open": float(parts[1]),
                "close": float(parts[2]),
                "high": float(parts[3]),
                "low": float(parts[4]),
                "vol": float(parts[5]),
            })
        return pd.DataFrame(rows)
    except Exception as e:
        print(f"    [eastmoney] {symbol} 失败: {e}")
        return None


def _convert_to_target_format(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """将 mootdx 或东财 的 K 线 DataFrame 转为目标 CSV 格式

    兼容两种源：mootdx 与东财都返回 datetime/open/close/high/low/vol
    """
    out = pd.DataFrame({
        "日期": pd.to_datetime(df["datetime"]).dt.strftime("%Y-%m-%d"),
        "股票代码": symbol,
        "开盘": df["open"].values,
        "收盘": df["close"].values,
        "最高": df["high"].values,
        "最低": df["low"].values,
        "成交量": df["vol"].values,
    })

    # 计算辅助字段
    prev_close = df["close"].shift(1)
    # 成交额 = (high + low + close) / 3 * vol（近似）
    out["成交额"] = ((df["high"] + df["low"] + df["close"]) / 3 * df["vol"]).round(0).values
    # 振幅 = (high - low) / prev_close * 100
    out["振幅"] = ((df["high"] - df["low"]) / prev_close * 100).round(2).values
    # 涨跌幅 = (close - prev_close) / prev_close * 100
    out["涨跌幅"] = ((df["close"] - prev_close) / prev_close * 100).round(2).values
    # 涨跌额 = close - prev_close
    out["涨跌额"] = (df["close"] - prev_close).round(2).values
    # 换手率 — 两源都无流通股本，留空（loader 不需要）
    out["换手率"] = 0.0

    return out


# === 腾讯 HTTP 备胎源（web.ifzq.gtimg.cn，HTTPS 零鉴权不封 IP）===

_TENCENT_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get"
_TENCENT_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://gu.qq.com/",
}
_TENCENT_TIMEOUT = 15


def get_market_prefix(code: str) -> str:
    """6 位代码 → 市场前缀（与 a-stock-data skill 保持一致）

    北交所: 92xxx/8xxxx → bj
    沪市:   6xxxx/9xxxx → sh
    深市:   0xxxx/2xxxx/3xxxx → sz
    """
    if code.startswith(("92", "8")):
        return "bj"
    if code.startswith(("6", "9")):
        return "sh"
    return "sz"


def fetch_kline_tencent(symbol: str, days: int = 5000) -> pd.DataFrame | None:
    """从腾讯 ifzq.gtimg.cn 拉取日 K 线（HTTP，零鉴权，不封 IP）

    Args:
        symbol: 6 位代码（如 '000875'）
        days: 目标拉取天数（实际能被满足 ~640 根 ≈ 2.5 年）

    Returns:
        DataFrame columns: datetime, open, close, high, low, vol
        或 None（失败/空数据）

    说明：腾讯 fqkline API count 上限约 1000（实际返回 ~640 根钳制，
    end_date 参数无效不分页）。所以腾讯源最多覆盖近 2.5 年，比
    东财源的 ~5000 根少，但作为兜底已足够。
    """
    prefix = get_market_prefix(symbol)
    full_code = f"{prefix}{symbol}"

    # 腾讯 API 限制：count 最大 ~1000（实际限流约 640 根）；end_date 不分页
    # 所以只需一次拉取，请求 count=1000（永远拿不到 1000 根，但比 500 多给一些）
    request_count = min(max(days, 500), 1000)

    try:
        # param 格式: code,period,,,count,adjust  （5 个字段）
        url = (
            f"{_TENCENT_URL}?param={full_code},day,,,{request_count},qfq"
        )
        req = urllib.request.Request(url, headers=_TENCENT_HEADERS)
        with urllib.request.urlopen(req, timeout=_TENCENT_TIMEOUT) as r:
            data = json.loads(r.read().decode("utf-8"))

        if data.get("code") not in (0, "0"):
            print(f"    [tencent] {symbol} 返错: code={data.get('code')} msg={data.get('msg')}")
            return None

        # 响应: {"code":0, "msg":"", "data":{full_code:{"qfqday":[...], ...}}}
        # 注：data 也可能是空 list（API 报 param error 时），需防御
        data_field = data.get("data", {})
        if not isinstance(data_field, dict):
            print(f"    [tencent] {symbol} 返空数据 (msg={data.get('msg')})")
            return None
        payload = data_field.get(full_code)
        if not isinstance(payload, dict):
            print(f"    [tencent] {symbol} 返空 payload")
            return None
        bars = payload.get("qfqday") or payload.get("day")
        if not bars:
            print(f"    [tencent] {symbol} 返空 bars")
            return None
    except Exception as e:
        print(f"    [tencent] {symbol} 异常: {e}")
        return None

    # 转换为标准格式
    rows = []
    for bar in bars:
        # bar 格式: [日期, 开, 收, 高, 低, 成交量]
        if len(bar) < 6:
            continue
        try:
            rows.append({
                "datetime": bar[0],
                "open": float(bar[1]),
                "close": float(bar[2]),
                "high": float(bar[3]),
                "low": float(bar[4]),
                "vol": float(bar[5]),
            })
        except (ValueError, TypeError, IndexError):
            continue

    if not rows:
        return None
    return pd.DataFrame(rows)


# === 默认股票列表（沪深300 + 中证红利部分成分股）===
DEFAULT_SYMBOLS = [
    "600519", "000333", "000858", "601318", "600036", "000001", "600276",
    "002594", "300750", "601012", "600887", "000651", "002475", "300760",
    "601888", "600030", "600000", "601398", "601166", "600028",
]


def download_one(client, symbol: str, data_dir: str = "backtest_data",
                 offset: int = 5000) -> bool:
    """下载单只股票的历史日线数据（mootdx → 东财 → 腾讯 三层 fallback）

    Args:
        client: mootdx client（如为 None 则直接走下一层）
        symbol: 6位股票代码（裸数字）
        data_dir: 输出目录
        offset: 拉取的最大 K 线根数（默认 5000 ≈ 20 年）

    Returns:
        True 成功, False 失败
    """
    csv_path = os.path.join(data_dir, f"stk_{symbol}.csv")

    # 跳过已存在
    if os.path.exists(csv_path):
        print(f"  跳过（已存在）: {csv_path}")
        return True

    df = None
    source = None

    # 1. 优先 mootdx
    if client is not None:
        try:
            df = client.bars(symbol=symbol, frequency=9, offset=offset)
            if df is not None and not df.empty:
                source = "mootdx"
        except Exception as e:
            print(f"    [mootdx] {symbol} 异常: {e}")
            df = None

    # 2. Fallback: 东财 HTTP
    if df is None or df.empty:
        print(f"    [mootdx] {symbol} 无数据，尝试东财 HTTP...")
        df = fetch_kline_eastmoney(symbol, days=offset)
        if df is not None and not df.empty:
            source = "eastmoney"

    # 3. Fallback: 腾讯 HTTP（兜底）
    if df is None or df.empty:
        print(f"    [eastmoney] {symbol} 无数据，尝试腾讯 HTTP fallback...")
        df = fetch_kline_tencent(symbol, days=offset)
        if df is not None and not df.empty:
            source = "tencent"

    if df is None or df.empty:
        print(f"  无数据 {symbol}（三源均失败）")
        return False

    # 转换为目标 CSV 格式（三源共用）
    out = _convert_to_target_format(df, symbol)

    # 保存（带 BOM 以兼容 Excel）
    os.makedirs(data_dir, exist_ok=True)
    out.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"  保存: {csv_path} ({len(out)} 行, 来源={source})")
    return True


def get_existing_symbols(data_dir: str = "backtest_data") -> list:
    """扫描 backtest_data/ 获取已有股票代码"""
    p = Path(data_dir)
    if not p.exists():
        return []
    symbols = []
    for f in p.glob("stk_*.csv"):
        sym = f.stem.replace("stk_", "")
        if len(sym) == 6 and sym.isdigit():
            symbols.append(sym)
    return sorted(symbols)


def main():
    parser = argparse.ArgumentParser(description="下载 A 股历史数据到 backtest_data/")
    parser.add_argument("--symbols", type=str, default="",
                        help="逗号分隔的股票代码列表（默认见 DEFAULT_SYMBOLS）")
    parser.add_argument("--all", action="store_true",
                        help="下载 backtest_data/ 中所有已有股票（用于更新）")
    parser.add_argument("--data-dir", type=str, default="backtest_data",
                        help="输出目录")
    parser.add_argument("--offset", type=int, default=5000,
                        help="拉取 K 线根数（默认 5000 ≈ 20 年）")
    parser.add_argument("--skip-mootdx", action="store_true",
                        help="跳过 mootdx 直接用东财 HTTP 备胎源")
    args = parser.parse_args()

    if args.all:
        symbols = get_existing_symbols(args.data_dir)
        print(f"将下载已有 {len(symbols)} 只股票")
    elif args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    else:
        symbols = DEFAULT_SYMBOLS
        print(f"使用默认股票列表 ({len(symbols)} 只)")

    client = None
    if not args.skip_mootdx:
        try:
            print(f"\n尝试连接 mootdx 服务器...")
            client = tdx_client()
            print("mootdx 连接成功")
        except RuntimeError as e:
            print(f"mootdx 不可用: {e}")
            print("将自动降级到东财 HTTP 备胎源，必要时再降级到腾讯")
    else:
        print("\n--skip-mootdx 模式，直接走东财 HTTP 源，必要时降级到腾讯")

    print()

    success = 0
    fail = 0
    for i, sym in enumerate(symbols, 1):
        print(f"[{i}/{len(symbols)}] {sym}")
        if download_one(client, sym, args.data_dir, args.offset):
            success += 1
        else:
            fail += 1

    print(f"\n完成: {success} 成功, {fail} 失败")


if __name__ == "__main__":
    main()
