"""通用技术指标（EMA/MACD/RSI）

漏洞 E：MACD_hist 均值含 ε 保护，避免除零
"""
import pandas as pd
import numpy as np

_EPSILON = 0.0001  # 漏洞 E：MACD 分母保护值


def calc_ema(s: pd.Series, period: int) -> pd.Series:
    """EMA 计算"""
    return s.ewm(span=period, adjust=False).mean()


def calc_macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """MACD 计算，返回 (macd_line, signal_line, hist)"""
    ema_fast = calc_ema(close, fast)
    ema_slow = calc_ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calc_ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """RSI 计算（Wilder's method）"""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, _EPSILON)   # 防止除零
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def calc_macd_hist_mean_abs(hist: pd.Series, window: int = 20) -> float:
    """MACD_hist 绝对值均值（含 ε 保护，漏洞 E）

    用于第 3/5 节 MACD 位置分计算的 分母_日
    """
    if len(hist) < window:
        recent = hist
    else:
        recent = hist.tail(window)
    mean_abs = float(recent.abs().mean())
    return max(_EPSILON, mean_abs)   # ε 保护