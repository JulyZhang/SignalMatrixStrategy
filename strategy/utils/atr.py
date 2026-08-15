"""ATR 计算（全局统一 ATR_30min 变量）

关键修正：
- 漏洞 I：零值保护（停牌/极端低波动）
- 漏洞 E：除零保护（与 MACD 分母一致）
"""
import pandas as pd

def calc_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """计算 ATR(True Range, period)

    处理零波动：返回 0 而非 NaN（漏洞 I 修正）
    """
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs()
    ], axis=1).max(axis=1)
    tr.iloc[0] = high.iloc[0] - low.iloc[0]

    # Wilder's smoothing (等价于 EMA with alpha=1/period)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    return atr.fillna(0)


def calc_atr_mean(atr_series: pd.Series, window: int = 50) -> float:
    """ATR 均值（数据不足时返回整个序列均值）

    用于 8.4 节 calc_position_size 的 ATR_ratio 计算
    """
    if len(atr_series) < window:
        return float(atr_series.mean()) if len(atr_series) > 0 else 0.0
    return float(atr_series.tail(window).mean())
