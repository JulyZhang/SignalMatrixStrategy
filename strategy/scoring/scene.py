"""场景识别（第 2 节）：5 步顺序过滤器

优先级：中阴态 > 拐点 > 趋势 > 震荡 > 默认中阴态
"""
import pandas as pd
from strategy.utils.indicators import calc_ema, calc_macd

# 关键阈值（与设计文档第 2 节一致）
MA_CONVERGENCE_THRESHOLD = 0.005   # 0.5% 均线粘合
VOLATILITY_DECLINE_RATIO = 0.7     # 波动率下降至 0.7 倍


def _check_zhongyintai(close: pd.Series, weekly_close: pd.Series) -> bool:
    """中阴态触发检查（任一即触发）"""
    # 周线 MA 收敛度
    ema20_w = weekly_close.ewm(span=20, adjust=False).mean()
    ema60_w = weekly_close.ewm(span=60, adjust=False).mean()
    if len(ema20_w) > 0 and len(ema60_w) > 0:
        convergence = abs(ema20_w.iloc[-1] - ema60_w.iloc[-1]) / ema60_w.iloc[-1]
        if convergence < MA_CONVERGENCE_THRESHOLD:
            return True

    # 日线 ATR 下降
    if len(close) >= 70:
        high = close * 1.01
        low = close * 0.99
        atr_recent = _calc_atr_simple(high, low, close, 20)
        atr_long = _calc_atr_simple(high, low, close, 50)
        if atr_long > 0 and atr_recent / atr_long < VOLATILITY_DECLINE_RATIO:
            return True

    return False


def _calc_atr_simple(high, low, close, period):
    """简化 ATR（用于波动率判定）"""
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean().iloc[-1]


def _check_guandian(close: pd.Series) -> bool:
    """拐点市判定：底背离 + MSS 已完成（简化版）"""
    if len(close) < 60:
        return False
    _, _, hist = calc_macd(close)
    # 简化：MACD_hist 在零轴下方但连续 3 期上升
    recent_hist = hist.tail(10)
    if len(recent_hist) < 10:
        return False
    if (recent_hist < 0).all() and recent_hist.is_monotonic_increasing:
        return True
    return False


def _check_trending(close: pd.Series) -> bool:
    """趋势市判定：EMA20 > EMA60 + ADX 替代（用价格斜率）"""
    if len(close) < 30:
        return False
    ema20 = calc_ema(close, 20)
    ema60 = calc_ema(close, 60)
    if ema20.iloc[-1] <= ema60.iloc[-1]:
        return False
    # 斜率判定
    slope = (ema20.iloc[-1] - ema20.iloc[-5]) / ema20.iloc[-5]
    return slope > 0.005  # 0.5%


def _check_range(close: pd.Series) -> bool:
    """震荡市判定：中枢内 + 低斜率"""
    if len(close) < 30:
        return False
    ema20 = calc_ema(close, 20)
    ema60 = calc_ema(close, 60)
    # EMA 缠绕（金叉死叉交替）
    diff = (ema20 - ema60).dropna()
    if len(diff) < 20:
        return False
    signs = (diff > 0).astype(int).diff().abs().sum()
    return signs >= 2  # 至少 2 次交叉


def recognize_scene(daily_close: pd.Series, weekly_close: pd.Series = None) -> str:
    """场景识别主入口（5 步顺序过滤器）"""
    if weekly_close is None:
        weekly_close = daily_close.resample("W").last().dropna()

    # Step 1: 中阴态过滤（最优先）
    if _check_zhongyintai(daily_close, weekly_close):
        return "中阴态"

    # Step 2: 拐点优先
    if _check_guandian(daily_close):
        return "拐点市"

    # Step 3: 趋势判定
    if _check_trending(daily_close):
        return "趋势市"

    # Step 4: 震荡兜底
    if _check_range(daily_close):
        return "震荡市"

    # Step 5: 默认中阴态
    return "中阴态"